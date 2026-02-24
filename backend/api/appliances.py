from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from db.session import get_db
from db.models import Appliance, User, ApplianceUsage
from datetime import datetime
from zoneinfo import ZoneInfo
from api.auth import get_current_user

IST = ZoneInfo("Asia/Kolkata")

def now_ist():
    return datetime.now(IST)

router = APIRouter(prefix="/appliances", tags=["Appliances"])


@router.get("/")
def list_appliances(db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    appliances = db.query(Appliance).filter(Appliance.user_id == current_user.id).all()

    return [
        {
            "id": a.id,
            "name": a.name,
            "power_kw": a.power_kw,
            "status": "ON" if a.is_on else "OFF"
        }
        for a in appliances
    ]


@router.post("/{appliance_id}/on")
def turn_on(appliance_id: int, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    appliance = db.query(Appliance).filter(
        Appliance.id == appliance_id, 
        Appliance.user_id == current_user.id
    ).first()

    if not appliance:
        raise HTTPException(status_code=403, detail="Not authorized or appliance not found")

    if appliance.is_on:
        return {"message": "Already ON"}

    appliance.is_on = True
    appliance.last_started_at = now_ist()

    db.commit()

    return {"message": f"{appliance.name} turned ON"}


@router.post("/{appliance_id}/off")
def turn_off(appliance_id: int, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    appliance = db.query(Appliance).filter(
        Appliance.id == appliance_id, 
        Appliance.user_id == current_user.id
    ).first()

    if not appliance or not appliance.is_on:
        raise HTTPException(status_code=403, detail="Not authorized or appliance not running")

    end_time = now_ist()
    duration_hours = (end_time - appliance.last_started_at).total_seconds() / 3600

    energy_used = round(appliance.power_kw * duration_hours, 3)

    usage = ApplianceUsage(
        appliance_id=appliance.id,
        start_time=appliance.last_started_at,
        end_time=end_time,
        energy_kwh=energy_used
    )

    appliance.is_on = False
    appliance.last_started_at = None

    db.add(usage)
    db.commit()

    return {
        "message": f"{appliance.name} turned OFF",
        "energy_used_kwh": energy_used
    }


@router.get("/{appliance_id}/usage")
def appliance_usage(appliance_id: int, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    appliance = db.query(Appliance).filter(
        Appliance.id == appliance_id, 
        Appliance.user_id == current_user.id
    ).first()
    
    if not appliance:
        raise HTTPException(status_code=403, detail="Not authorized")

    today = now_ist().date()

    usages = db.query(ApplianceUsage).filter(
        ApplianceUsage.appliance_id == appliance_id,
        ApplianceUsage.start_time >= today
    ).all()

    total = sum(u.energy_kwh for u in usages)

    return {
        "appliance_id": appliance_id,
        "today_usage_kwh": round(total, 3)
    }