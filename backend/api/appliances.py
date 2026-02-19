from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from db.session import get_db
from db.models import Appliance
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo
from db.models import ApplianceUsage

IST = ZoneInfo("Asia/Kolkata")

router = APIRouter(prefix="/appliances", tags=["Appliances"])


@router.get("/")
def list_appliances(db: Session = Depends(get_db)):
    appliances = db.query(Appliance).all()

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
def turn_on(appliance_id: int, db: Session = Depends(get_db)):
    appliance = db.query(Appliance).get(appliance_id)

    if not appliance:
        return {"error": "Appliance not found"}

    if appliance.is_on:
        return {"message": "Already ON"}

    appliance.is_on = True
    appliance.last_started_at = datetime.now(IST)

    db.commit()

    return {"message": f"{appliance.name} turned ON"}

@router.post("/{appliance_id}/off")
def turn_off(appliance_id: int, db: Session = Depends(get_db)):
    appliance = db.query(Appliance).get(appliance_id)

    if not appliance or not appliance.is_on:
        return {"error": "Appliance not running"}

    end_time = datetime.now(IST)
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
def appliance_usage(appliance_id: int, db: Session = Depends(get_db)):
    today = datetime.now(IST).date()

    usages = db.query(ApplianceUsage).filter(
        ApplianceUsage.appliance_id == appliance_id,
        ApplianceUsage.start_time >= today
    ).all()

    total = sum(u.energy_kwh for u in usages)

    return {
        "appliance_id": appliance_id,
        "today_usage_kwh": round(total, 3)
    }