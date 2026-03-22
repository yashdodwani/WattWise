"""
api/dashboard.py — WattWise Dashboard Routes

Endpoints:
  GET /dashboard/summary      → Main cards data (current load, today kWh, predicted bill, active devices)
  GET /dashboard/consumption  → Graph data (last 50 meter readings)
  GET /dashboard/appliances   → Appliance usage breakdown
  GET /dashboard/savings      → Cost savings vs un-optimised usage
  GET /dashboard/today-cost   → Today's electricity bill
"""

import datetime
from zoneinfo import ZoneInfo

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from sqlalchemy import desc, func

from db.session import get_db
from db.models import MeterReading, Appliance, Tariff, Meter
from api.auth import get_current_user
from services.tariff_service import calculate_today_cost

IST = ZoneInfo("Asia/Kolkata")

router = APIRouter(prefix="/dashboard", tags=["Dashboard"])


# --------------------------------------------------------------------------- #
#  Helper
# --------------------------------------------------------------------------- #

def _midnight_ist() -> datetime.datetime:
    """Return today's midnight in IST as a naive datetime (matches DB storage)."""
    return (
        datetime.datetime.now(tz=IST)
        .replace(hour=0, minute=0, second=0, microsecond=0)
        .replace(tzinfo=None)
    )


# --------------------------------------------------------------------------- #
#  ENDPOINT 1 — Summary (main cards)
# --------------------------------------------------------------------------- #

@router.get("/summary")
def dashboard_summary(
    current_user=Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    Main dashboard cards:
      - current_load_kw    : latest reading × 4  (15-min interval → hourly)
      - today_kwh          : sum of readings since midnight IST
      - predicted_bill     : today_kwh × avg rate (₹7/unit estimate)
      - active_devices     : appliances currently ON for this user
    """
    base_query = (
        db.query(MeterReading)
        .join(Meter)
        .filter(Meter.user_id == current_user.id)
    )

    latest = (
        base_query
        .order_by(desc(MeterReading.timestamp))
        .first()
    )

    today_start = _midnight_ist()
    readings = (
        base_query
        .filter(MeterReading.timestamp >= today_start)
        .all()
    )

    today_kwh = sum(r.energy_kwh for r in readings)

    active_devices = (
        db.query(Appliance)
        .filter(
            Appliance.user_id == current_user.id,
            Appliance.is_on == True,
        )
        .count()
    )

    predicted_bill = round(today_kwh * 7, 2)

    return {
        "current_load_kw": round(latest.energy_kwh * 4, 2) if latest else 0,
        "today_kwh": round(today_kwh, 2),
        "predicted_bill": predicted_bill,
        "active_devices": active_devices,
    }


# --------------------------------------------------------------------------- #
#  ENDPOINT 2 — Consumption graph
# --------------------------------------------------------------------------- #

@router.get("/consumption")
def consumption_graph(
    current_user=Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    Return last 50 meter readings ordered by timestamp for the graph component.

    Response: [{"time": "2026-03-05T10:00:00", "kwh": 0.35}, ...]
    """
    readings = (
        db.query(MeterReading)
        .join(Meter)
        .filter(Meter.user_id == current_user.id)
        .order_by(MeterReading.timestamp)
        .all()
    )

    return [
        {"time": r.timestamp.isoformat(), "kwh": r.energy_kwh}
        for r in readings[-50:]
    ]


# --------------------------------------------------------------------------- #
#  ENDPOINT 3 — Appliance usage breakdown
# --------------------------------------------------------------------------- #

@router.get("/appliances")
def appliance_usage(
    current_user=Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    Per-appliance energy breakdown for the current user.
    Runtime is simulated at 0.5 h for each appliance.

    Response: [{"name": "AC", "energy_kwh": 1.0, "power_kw": 2.0, "status": "ON"}, ...]
    """
    appliances = (
        db.query(Appliance)
        .filter(Appliance.user_id == current_user.id)
        .all()
    )

    usage = []
    for a in appliances:
        runtime = 0.5  # simulated runtime in hours
        energy = round(a.power_kw * runtime, 2)
        usage.append({
            "name": a.name,
            "energy_kwh": energy,
            "power_kw": a.power_kw,
            "status": "ON" if a.is_on else "OFF",
        })

    return usage


# --------------------------------------------------------------------------- #
#  ENDPOINT 4 — Savings
# --------------------------------------------------------------------------- #

@router.get("/savings")
def savings(
    current_user=Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    Cost savings achieved by using WattWise optimisation.

    Compares:
      - normal_cost     : all readings × ₹8/unit  (un-optimised peak rate)
      - optimized_cost  : all readings × ₹6.8/unit (with smart scheduling)

    Response: {"today_cost": 68.0, "savings_today": 12.0, "efficiency": 68}
    """
    today_start = _midnight_ist()
    
    today_kwh = (
        db.query(func.sum(MeterReading.energy_kwh))
        .join(Meter)
        .filter(Meter.user_id == current_user.id)
        .filter(MeterReading.timestamp >= today_start)
        .scalar()
    ) or 0.0

    normal_cost    = today_kwh * 8
    optimized_cost = today_kwh * 6.8

    return {
        "today_cost": round(optimized_cost, 2),
        "savings_today": round(normal_cost - optimized_cost, 2),
        "efficiency": 68,
    }


# --------------------------------------------------------------------------- #
#  ENDPOINT 5 — Today's electricity bill (tariff-accurate)
# --------------------------------------------------------------------------- #

@router.get("/today-cost")
def today_cost(
    current_user=Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    Accurate today bill calculated using actual tariff slabs.

    Reuses the same logic as /tariffs/today-cost.

    Response: {"today_kwh": 14.2, "today_cost": 72.35}
    """
    today_start = _midnight_ist()
    readings = (
        db.query(MeterReading)
        .join(Meter)
        .filter(Meter.user_id == current_user.id)
        .filter(MeterReading.timestamp >= today_start)
        .all()
    )
    tariffs = db.query(Tariff).all()
    return calculate_today_cost(readings, tariffs)
