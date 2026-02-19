"""
api/tariffs.py — WattWise Tariff Routes

All 6 endpoints:
  GET  /tariffs/current       → current tariff slab (IST)
  GET  /tariffs/              → full tariff schedule
  GET  /tariffs/today-cost    → today's bill from meter readings
  POST /tariffs/simulate      → cost of running appliance at a time
  POST /tariffs/cheapest-slot → best time to run appliance in a window

Tariffs are fetched from DB once per request and passed to service functions.
"""

import datetime
from zoneinfo import ZoneInfo

from fastapi import APIRouter, Depends
from pydantic import BaseModel
from sqlalchemy.orm import Session

from db.session import get_db
from db.models import Tariff, MeterReading
from services.tariff_service import (
    get_current_tariff,
    get_full_schedule,
    calculate_today_cost,
    simulate_cost,
    find_cheapest_slot,
)

IST    = ZoneInfo("Asia/Kolkata")
router = APIRouter(prefix="/tariffs", tags=["Tariffs"])


# --------------------------------------------------------------------------- #
#  Request schemas
# --------------------------------------------------------------------------- #

class SimulateRequest(BaseModel):
    power_kw        : float
    duration_minutes: int
    start_time      : str   # "HH:MM"

    model_config = {"json_schema_extra": {
        "example": {"power_kw": 1.5, "duration_minutes": 60, "start_time": "23:00"}
    }}


class CheapestSlotRequest(BaseModel):
    power_kw        : float
    duration_minutes: int
    window_start    : str   # "HH:MM"
    window_end      : str   # "HH:MM"

    model_config = {"json_schema_extra": {
        "example": {
            "power_kw": 2, "duration_minutes": 60,
            "window_start": "18:00", "window_end": "06:00"
        }
    }}


# --------------------------------------------------------------------------- #
#  Helper: fetch all tariffs once per request
# --------------------------------------------------------------------------- #

def _get_tariffs(db: Session) -> list:
    """Fetch all tariff rows from DB. Called once per request."""
    return db.query(Tariff).all()


# --------------------------------------------------------------------------- #
#  ENDPOINT 1 — Current tariff
# --------------------------------------------------------------------------- #

@router.get("/current")
def current_tariff(db: Session = Depends(get_db)):
    """
    Return the tariff slab active right now (Asia/Kolkata timezone).

    Response:
        {"current_price": 5, "time_range": "10:00 - 18:00"}
    """
    tariffs = _get_tariffs(db)
    return get_current_tariff(tariffs)


# --------------------------------------------------------------------------- #
#  ENDPOINT 2 — Full schedule
# --------------------------------------------------------------------------- #

@router.get("/")
def full_schedule(db: Session = Depends(get_db)):
    """
    Return all tariff slabs ordered by start_time.
    Overnight slab (22:00–06:00) is placed last.

    Response:
        [{"start": "06:00", "end": "10:00", "price": 6}, ...]
    """
    tariffs = _get_tariffs(db)
    return get_full_schedule(tariffs)


# --------------------------------------------------------------------------- #
#  ENDPOINT 3 — Today's bill
# --------------------------------------------------------------------------- #

@router.get("/today-cost")
def today_cost(db: Session = Depends(get_db)):
    """
    Calculate today's electricity bill from all meter readings since midnight IST.

    For each reading: cost += energy_kwh × tariff_at(reading.timestamp)

    Response:
        {"today_kwh": 14.2, "today_cost": 72.35}
    """
    # Midnight IST today (timestamps are now stored in IST)
    today_ist   = datetime.datetime.now(tz=IST).replace(
        hour=0, minute=0, second=0, microsecond=0
    ).replace(tzinfo=None)  # Remove timezone info for SQLAlchemy comparison

    readings = (
        db.query(MeterReading)
        .filter(MeterReading.timestamp >= today_ist)
        .all()
    )
    tariffs  = _get_tariffs(db)
    return calculate_today_cost(readings, tariffs)


# --------------------------------------------------------------------------- #
#  ENDPOINT 4 — Cost simulation
# --------------------------------------------------------------------------- #

@router.post("/simulate")
def simulate(req: SimulateRequest, db: Session = Depends(get_db)):
    """
    Simulate cost of running an appliance at a specific start time.

    Steps through in 15-min intervals to handle slab boundary crossings.

    Request:
        {"power_kw": 1.5, "duration_minutes": 60, "start_time": "23:00"}

    Response:
        {"energy_used": 1.5, "cost": 4.5, "price_per_unit": 3}
    """
    tariffs = _get_tariffs(db)
    return simulate_cost(
        power_kw         = req.power_kw,
        duration_minutes = req.duration_minutes,
        start_time_str   = req.start_time,
        tariff_rows      = tariffs,
    )


# --------------------------------------------------------------------------- #
#  ENDPOINT 5 — Cheapest slot finder
# --------------------------------------------------------------------------- #

@router.post("/cheapest-slot")
def cheapest_slot(req: CheapestSlotRequest, db: Session = Depends(get_db)):
    """
    Find the lowest-cost continuous time slot to run an appliance
    within the given search window. Handles overnight windows (e.g. 18:00–06:00).

    Uses Sliding Window algorithm with 15-minute step granularity.

    Request:
        {"power_kw": 2, "duration_minutes": 60, "window_start": "18:00", "window_end": "06:00"}

    Response:
        {"recommended_start": "22:15", "expected_cost": 3.2, "savings_vs_now": 5.7}
    """
    tariffs = _get_tariffs(db)
    return find_cheapest_slot(
        power_kw         = req.power_kw,
        duration_minutes = req.duration_minutes,
        window_start_str = req.window_start,
        window_end_str   = req.window_end,
        tariff_rows      = tariffs,
    )
