from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.orm import Session
from db.session import get_db
from db.models import Appliance, User
from datetime import datetime
from db.models import ApplianceUsage
from api.auth import get_current_user
from zoneinfo import ZoneInfo
from services.power_lookup import get_power_from_model

IST = ZoneInfo("Asia/Kolkata")

def now_ist():
    return datetime.now(IST)

router = APIRouter(prefix="/appliances", tags=["Appliances"])

class PowerRequest(BaseModel):
    brand: str
    model: str

@router.post("/estimate-power")
def estimate_power(data: PowerRequest):
    power = get_power_from_model(data.brand, data.model)

    if not power:
        return {
            "found": False,
            "message": "Model not found, please enter manually"
        }

    return {
        "found": True,
        "power_kw": power
    }

@router.post("/")
def add_appliance(data: dict, db: Session = Depends(get_db), current_user=Depends(get_current_user)):

    appliance = Appliance(
        user_id=current_user.id,
        name=data["name"],
        brand=data.get("brand"),
        model=data.get("model"),
        power_kw=data["power_kw"]
    )

    db.add(appliance)
    db.commit()

    return {"message": "Appliance added successfully"}


@router.get("/")
def list_appliances(db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    appliances = db.query(Appliance).filter(Appliance.user_id == current_user.id).all()

    return [
        {
            "id": a.id,
            "name": a.name,
            "brand": a.brand,
            "model": a.model,
            "power_kw": a.power_kw,
            "status": "ON" if a.is_on else "OFF"
        }
        for a in appliances
    ]

@router.post("/{appliance_id}/on")
def turn_on(appliance_id: int, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    appliance = db.query(Appliance).filter(Appliance.id == appliance_id).first()

    if not appliance or appliance.user_id != current_user.id:
        raise HTTPException(status_code=403, detail="Not authorized")

    if appliance.is_on:
        return {"message": "Already ON"}

    appliance.is_on = True
    appliance.last_started_at = now_ist()

    db.commit()

    return {"message": f"{appliance.name} turned ON"}

@router.post("/{appliance_id}/off")
def turn_off(appliance_id: int, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    appliance = db.query(Appliance).filter(Appliance.id == appliance_id).first()

    if not appliance or appliance.user_id != current_user.id:
        raise HTTPException(status_code=403, detail="Not authorized")

    if not appliance.is_on:
        return {"message": f"{appliance.name} is already OFF", "energy_used_kwh": 0}

    end_time = now_ist()

    # Guard: last_started_at may be None if the appliance was seeded as ON
    # without a recorded start time — fall back to 0 energy in that case.
    if appliance.last_started_at is None:
        duration_hours = 0.0
        start_time = end_time
    else:
        last_started = appliance.last_started_at
        # Ensure both datetimes are comparable (handle naive DB timestamps)
        if last_started.tzinfo is None:
            last_started = last_started.replace(tzinfo=ZoneInfo("UTC")).astimezone(IST)
        duration_hours = (end_time - last_started).total_seconds() / 3600
        start_time = last_started

    energy_used = round(appliance.power_kw * max(duration_hours, 0), 3)

    usage = ApplianceUsage(
        appliance_id=appliance.id,
        start_time=start_time,
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
    appliance = db.query(Appliance).filter(Appliance.id == appliance_id).first()
    if not appliance or appliance.user_id != current_user.id:
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