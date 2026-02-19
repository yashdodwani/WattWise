from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from db.session import get_db
from db.models import MeterReading, Tariff
from sqlalchemy import desc
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo
from services.tariff_service import calculate_today_cost

IST = ZoneInfo("Asia/Kolkata")

router = APIRouter(prefix="/meter", tags=["Meter"])


@router.get("/live")
def get_live_meter(db: Session = Depends(get_db)):
    latest = (
        db.query(MeterReading)
        .order_by(desc(MeterReading.timestamp))
        .first()
    )

    if not latest:
        return {"message": "No readings yet"}

    # last 60 minutes graph
    now = datetime.now(IST)
    one_hour_ago = now - timedelta(hours=1)
    readings = (
        db.query(MeterReading)
        .filter(MeterReading.timestamp >= one_hour_ago)
        .order_by(MeterReading.timestamp)
        .all()
    )

    graph = [
        {
            "time": (r.timestamp.replace(tzinfo=IST) if r.timestamp.tzinfo is None else r.timestamp.astimezone(IST)).isoformat(),
            "kwh": r.energy_kwh
        }
        for r in readings
    ]

    # today usage and cost
    today_start = now.replace(hour=0, minute=0, second=0, microsecond=0)
    today_readings = db.query(MeterReading).filter(MeterReading.timestamp >= today_start).all()

    # Get tariffs for cost calculation
    tariff_rows = db.query(Tariff).all()

    # Use official tariff service function
    today_stats = calculate_today_cost(today_readings, tariff_rows)

    return {
        "current_kwh": latest.energy_kwh,
        "current_kw": round(latest.energy_kwh * 4, 2),  # 15min → kW approx
        "today_kwh": today_stats["today_kwh"],
        "today_cost": today_stats["today_cost"],
        "graph": graph
    }
