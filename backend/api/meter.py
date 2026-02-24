from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from db.session import get_db
from db.models import MeterReading, Meter, User
from api.auth import get_current_user
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo

IST = ZoneInfo("Asia/Kolkata")

def now_ist():
    return datetime.now(IST)

router = APIRouter(prefix="/meter", tags=["Meter"])


@router.get("/readings")
def get_meter_readings(db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    """Get all meter readings for current user"""
    # Fetch meter ids owned by the user
    meters = db.query(Meter).filter(Meter.user_id == current_user.id).all()
    meter_ids = [m.id for m in meters]

    if not meter_ids:
        return []

    readings = db.query(MeterReading).filter(MeterReading.meter_id.in_(meter_ids)).all()

    return [
        {
            "id": r.id,
            "meter_id": r.meter_id,
            "timestamp": r.timestamp.isoformat() if r.timestamp else None,
            "energy_kwh": r.energy_kwh
        }
        for r in readings
    ]


@router.get("/readings/{meter_id}")
def get_meter_readings_by_id(meter_id: int, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    """Get readings for a specific meter (must belong to current user)"""
    meter = db.query(Meter).filter(Meter.id == meter_id).first()
    if not meter or meter.user_id != current_user.id:
        raise HTTPException(status_code=403, detail="Not authorized")

    readings = db.query(MeterReading).filter(MeterReading.meter_id == meter_id).all()

    if not readings:
        return {"message": "No readings found for this meter"}

    return [
        {
            "id": r.id,
            "meter_id": r.meter_id,
            "timestamp": r.timestamp.isoformat() if r.timestamp else None,
            "energy_kwh": r.energy_kwh
        }
        for r in readings
    ]


@router.get("/today-usage/{meter_id}")
def get_today_usage(meter_id: int, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    """Get today's energy usage for a meter (must belong to current user)"""
    meter = db.query(Meter).filter(Meter.id == meter_id).first()
    if not meter or meter.user_id != current_user.id:
        raise HTTPException(status_code=403, detail="Not authorized")

    today_start = datetime.combine(now_ist().date(), datetime.min.time()).replace(tzinfo=IST)
    today_end = now_ist()

    readings = db.query(MeterReading).filter(
        MeterReading.meter_id == meter_id,
        MeterReading.timestamp >= today_start,
        MeterReading.timestamp <= today_end
    ).all()

    total_kwh = sum(r.energy_kwh for r in readings) if readings else 0

    return {
        "meter_id": meter_id,
        "date": now_ist().date().isoformat(),
        "total_energy_kwh": round(total_kwh, 2),
        "reading_count": len(readings)
    }


@router.get("/weekly-usage/{meter_id}")
def get_weekly_usage(meter_id: int, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    """Get weekly energy usage for a meter (must belong to current user)"""
    meter = db.query(Meter).filter(Meter.id == meter_id).first()
    if not meter or meter.user_id != current_user.id:
        raise HTTPException(status_code=403, detail="Not authorized")

    today = now_ist()
    week_start = today - timedelta(days=7)

    readings = db.query(MeterReading).filter(
        MeterReading.meter_id == meter_id,
        MeterReading.timestamp >= week_start,
        MeterReading.timestamp <= today
    ).all()

    total_kwh = sum(r.energy_kwh for r in readings) if readings else 0

    return {
        "meter_id": meter_id,
        "period": f"{(week_start).date()} to {today.date()}",
        "total_energy_kwh": round(total_kwh, 2),
        "average_daily_kwh": round(total_kwh / 7, 2) if total_kwh > 0 else 0,
        "reading_count": len(readings)
    }


@router.get("/monthly-usage/{meter_id}")
def get_monthly_usage(meter_id: int, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    """Get monthly energy usage for a meter (must belong to current user)"""
    meter = db.query(Meter).filter(Meter.id == meter_id).first()
    if not meter or meter.user_id != current_user.id:
        raise HTTPException(status_code=403, detail="Not authorized")

    today = now_ist()
    month_start = today.replace(day=1)

    readings = db.query(MeterReading).filter(
        MeterReading.meter_id == meter_id,
        MeterReading.timestamp >= month_start,
        MeterReading.timestamp <= today
    ).all()

    total_kwh = sum(r.energy_kwh for r in readings) if readings else 0

    return {
        "meter_id": meter_id,
        "period": f"{month_start.strftime('%B %Y')}",
        "total_energy_kwh": round(total_kwh, 2),
        "reading_count": len(readings)
    }
