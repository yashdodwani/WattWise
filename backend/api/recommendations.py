"""
api/recommendations.py — WattWise Recommendation Routes

Fully aligned with tariff_service.py:
  - Uses IST timezone (Asia/Kolkata)
  - Uses simulate_cost() for accurate per-minute cost calculation
  - Uses find_cheapest_slot() (Sliding Window) for best time
  - Compares current cost vs best slot for can_use_now logic
  - All tariffs fetched once per request from DB

Endpoints:
  GET  /recommendations/                        → best slot for every appliance
  GET  /recommendations/{appliance_id}          → top 3 slots for one appliance
  GET  /recommendations/{appliance_id}/best     → single best slot + voice message
  POST /recommendations/{appliance_id}/compare  → compare multiple run times
"""

import datetime
from zoneinfo import ZoneInfo
from typing import List

from fastapi import APIRouter, Depends, Query, Path
from sqlalchemy.orm import Session
from pydantic import BaseModel

from db.session import get_db
from db.models import Tariff, Appliance
from schemas.recommendation import Recommendation
from services.tariff_service import (
    simulate_cost,
    find_cheapest_slot,
    get_price_for_timestamp,
    now_ist,
)

IST    = ZoneInfo("Asia/Kolkata")
router = APIRouter(prefix="/recommendations", tags=["Recommendations"])

# Sliding window scans full 24 hours by default
DEFAULT_WINDOW_START = "00:00"
DEFAULT_WINDOW_END   = "23:45"


# --------------------------------------------------------------------------- #
#  Request schema for compare endpoint
# --------------------------------------------------------------------------- #

class CompareTimesRequest(BaseModel):
    duration_minutes: int
    times: List[str]   # ["HH:MM", ...]

    model_config = {"json_schema_extra": {
        "example": {
            "duration_minutes": 60,
            "times": ["08:00", "14:00", "22:00"]
        }
    }}


# --------------------------------------------------------------------------- #
#  Core internal helper — shared by all endpoints
# --------------------------------------------------------------------------- #

def _build_recommendation(
    appliance       : Appliance,
    duration_minutes: int,
    tariff_rows     : list,
    top_n           : int = 3,
) -> dict:
    """
    Core recommendation logic. Called by all endpoints.

    Steps:
    1. Simulate cost if run RIGHT NOW (IST)
    2. Find cheapest slot using Sliding Window (full 24hr, 15-min steps)
    3. can_use_now = True if current cost is within 15% of best
    4. Build top N slots sorted by cost across 24 hours

    All cost calculations use simulate_cost() which steps in 15-min chunks
    to correctly handle appliances that run across tariff slab boundaries.
    """
    now     = now_ist()
    now_str = now.strftime("%H:%M")

    # Step 1 — Cost if run right now
    now_sim = simulate_cost(
        power_kw         = appliance.power_kw,
        duration_minutes = duration_minutes,
        start_time_str   = now_str,
        tariff_rows      = tariff_rows,
    )
    now_cost = now_sim["cost"]

    # Step 2 — Best slot across full 24 hours
    best = find_cheapest_slot(
        power_kw         = appliance.power_kw,
        duration_minutes = duration_minutes,
        window_start_str = DEFAULT_WINDOW_START,
        window_end_str   = DEFAULT_WINDOW_END,
        tariff_rows      = tariff_rows,
        step_minutes     = 15,
    )
    best_cost = best["expected_cost"]
    savings   = round(max(0.0, now_cost - best_cost), 2)

    # Step 3 — can_use_now threshold: within 15% of best = green light
    can_use = now_cost <= best_cost * 1.15

    # Step 4 — Build top N by scanning full day at 15-min steps
    today    = now.date()
    slots    = []
    cursor   = datetime.datetime(today.year, today.month, today.day, 0, 0, tzinfo=IST)
    end_scan = cursor + datetime.timedelta(hours=24)

    while cursor < end_scan:
        t_str  = cursor.strftime("%H:%M")
        sim    = simulate_cost(appliance.power_kw, duration_minutes, t_str, tariff_rows)
        end_dt = cursor + datetime.timedelta(minutes=duration_minutes)

        slots.append({
            "start_time"         : t_str,
            "end_time"           : end_dt.strftime("%H:%M"),
            "slot_label"         : f"{t_str} – {end_dt.strftime('%H:%M')}",
            "estimated_cost_inr" : sim["cost"],
            "avg_tariff"         : sim["price_per_unit"],
            "energy_kwh"         : sim["energy_used"],
            "savings_vs_now_inr" : round(max(0.0, now_cost - sim["cost"]), 2),
            "is_cheapest"        : False,
        })
        cursor += datetime.timedelta(minutes=15)

    slots.sort(key=lambda x: x["estimated_cost_inr"])
    top_slots = slots[:top_n]
    if top_slots:
        top_slots[0]["is_cheapest"] = True

    for i, s in enumerate(top_slots):
        s["rank"]   = i + 1
        s["reason"] = _build_reason(s, i, appliance.name)

    # Current ToD context
    current_price = get_price_for_timestamp(now, tariff_rows)

    return {
        "appliance_id"           : appliance.id,
        "appliance_name"         : appliance.name,
        "power_kw"               : appliance.power_kw,
        "duration_minutes"       : duration_minutes,
        "current_time_ist"       : now_str,
        "current_tariff"         : current_price,
        "current_tod_label"      : _tod_label(current_price),
        "can_use_now"            : can_use,
        "current_cost_inr"       : now_cost,
        "best_slot_start"        : best["recommended_start"],
        "best_slot_cost_inr"     : best_cost,
        "savings_if_you_wait_inr": savings,
        "recommendation_message" : _rec_message(can_use, best, savings, appliance.name),
        "top_slots"              : top_slots,
    }


# --------------------------------------------------------------------------- #
#  ENDPOINT 1 — All appliances summary (original route, kept compatible)
# --------------------------------------------------------------------------- #

@router.get("/", response_model=List[Recommendation])
async def get_recommendations(
    duration_minutes: int = Query(60, description="Default run duration in minutes"),
    db: Session = Depends(get_db),
):
    """
    Returns best time slot for every appliance.
    Tariffs fetched once and reused for all appliances (no duplicate DB hits).

    Compatible with existing response_model=List[Recommendation].
    """
    appliances  = db.query(Appliance).all()
    tariff_rows = db.query(Tariff).all()
    results     = []

    for appliance in appliances:
        rec  = _build_recommendation(appliance, duration_minutes, tariff_rows, top_n=1)
        best = rec["top_slots"][0] if rec["top_slots"] else {}

        results.append(Recommendation(
            appliance_id           = appliance.id,
            appliance_name         = appliance.name,
            can_use_now            = rec["can_use_now"],
            best_slot              = rec["best_slot_start"],
            estimated_cost_inr     = rec["best_slot_cost_inr"],
            savings_vs_peak_inr    = rec["savings_if_you_wait_inr"],
            recommendation_message = rec["recommendation_message"],
            reason                 = best.get("reason", ""),
        ))

    return results


# --------------------------------------------------------------------------- #
#  ENDPOINT 2 — Top N slots for one appliance
# --------------------------------------------------------------------------- #

@router.get("/{appliance_id}")
def get_recommendation_for_appliance(
    appliance_id    : int     = Path(..., description="Appliance ID from DB"),
    duration_minutes: int     = Query(60, description="Run duration in minutes"),
    top_n           : int     = Query(3, ge=1, le=10, description="Number of slots"),
    db              : Session = Depends(get_db),
):
    """
    Returns top N cheapest time slots for a specific appliance.

    Uses simulate_cost() which steps in 15-min intervals — so an appliance
    running from 21:30–22:30 correctly pays the normal rate for the first 30
    minutes and the off-peak rate for the last 30 minutes.

    Example: GET /recommendations/1?duration_minutes=90&top_n=3
    """
    appliance = db.query(Appliance).filter(Appliance.id == appliance_id).first()
    if not appliance:
        return {"success": False, "error": f"Appliance {appliance_id} not found"}

    tariff_rows = db.query(Tariff).all()
    rec         = _build_recommendation(appliance, duration_minutes, tariff_rows, top_n)
    return {"success": True, "data": rec}


# --------------------------------------------------------------------------- #
#  ENDPOINT 3 — Single best slot + voice message
# --------------------------------------------------------------------------- #

@router.get("/{appliance_id}/best")
def get_best_slot(
    appliance_id    : int     = Path(..., description="Appliance ID from DB"),
    duration_minutes: int     = Query(60, description="Run duration in minutes"),
    db              : Session = Depends(get_db),
):
    """
    Returns the single cheapest time slot with a voice-assistant-ready message.

    Ideal for:
      - Push notification: "Save ₹6.50 by running at 11:00 PM"
      - Voice assistant response from /recommendations/{id}/best

    Example: GET /recommendations/1/best?duration_minutes=120
    """
    appliance = db.query(Appliance).filter(Appliance.id == appliance_id).first()
    if not appliance:
        return {"success": False, "error": f"Appliance {appliance_id} not found"}

    tariff_rows = db.query(Tariff).all()
    rec         = _build_recommendation(appliance, duration_minutes, tariff_rows, top_n=1)
    best        = rec["top_slots"][0] if rec["top_slots"] else {}

    return {
        "success"             : True,
        "appliance_name"      : appliance.name,
        "can_use_now"         : rec["can_use_now"],
        "current_tod_label"   : rec["current_tod_label"],
        "current_tariff"      : rec["current_tariff"],
        "current_cost_inr"    : rec["current_cost_inr"],
        "best_slot"           : rec["best_slot_start"],
        "slot_label"          : best.get("slot_label", "N/A"),
        "best_cost_inr"       : rec["best_slot_cost_inr"],
        "savings_vs_now_inr"  : rec["savings_if_you_wait_inr"],
        "reason"              : best.get("reason", ""),
        "voice_message"       : (
            f"Run your {appliance.name} at {rec['best_slot_start']} "
            f"to save ₹{rec['savings_if_you_wait_inr']} "
            f"compared to running it right now."
        ),
    }


# --------------------------------------------------------------------------- #
#  ENDPOINT 4 — Compare specific times side-by-side
# --------------------------------------------------------------------------- #

@router.post("/{appliance_id}/compare")
def compare_times(
    appliance_id: int                  = Path(..., description="Appliance ID from DB"),
    req         : CompareTimesRequest  = ...,
    db          : Session              = Depends(get_db),
):
    """
    Compare cost of running an appliance at specific times chosen by the user.
    Returns them ranked cheapest first with savings vs the most expensive option.

    Useful for: "Is 8 AM, 2 PM, or 10 PM cheapest for my washing machine?"

    Example:
    POST /recommendations/1/compare
    Body: {"duration_minutes": 60, "times": ["08:00", "14:00", "22:00"]}
    """
    appliance = db.query(Appliance).filter(Appliance.id == appliance_id).first()
    if not appliance:
        return {"success": False, "error": f"Appliance {appliance_id} not found"}

    tariff_rows = db.query(Tariff).all()
    comparisons = []

    for t_str in req.times:
        try:
            sim    = simulate_cost(appliance.power_kw, req.duration_minutes, t_str, tariff_rows)
            end_t  = _add_minutes_to_str(t_str, req.duration_minutes)
            comparisons.append({
                "start_time"         : t_str,
                "end_time"           : end_t,
                "slot_label"         : f"{t_str} – {end_t}",
                "estimated_cost_inr" : sim["cost"],
                "avg_tariff"         : sim["price_per_unit"],
                "tod_label"          : _tod_label(sim["price_per_unit"]),
                "energy_kwh"         : sim["energy_used"],
            })
        except Exception:
            comparisons.append({"start_time": t_str, "error": "Invalid format. Use HH:MM"})

    valid = [c for c in comparisons if "error" not in c]
    valid.sort(key=lambda x: x["estimated_cost_inr"])

    if valid:
        max_cost = valid[-1]["estimated_cost_inr"]
        for i, c in enumerate(valid):
            c["rank"]             = i + 1
            c["savings_vs_worst"] = round(max_cost - c["estimated_cost_inr"], 2)
            c["is_recommended"]   = (i == 0)

    return {
        "success"       : True,
        "appliance_name": appliance.name,
        "power_kw"      : appliance.power_kw,
        "duration_mins" : req.duration_minutes,
        "comparisons"   : valid,
        "errors"        : [c for c in comparisons if "error" in c],
    }


# --------------------------------------------------------------------------- #
#  Private helpers
# --------------------------------------------------------------------------- #

def _tod_label(price: float) -> str:
    if price <= 4.0:
        return "Off-Peak 🟢"
    elif price <= 6.5:
        return "Normal 🟡"
    return "Peak 🔴"


def _rec_message(can_use: bool, best: dict, savings: float, name: str) -> str:
    if can_use:
        return f"✅ Good time to run {name}! Tariff is near its daily low."
    return (
        f"⏳ Wait until {best['recommended_start']} to run {name} "
        f"and save ₹{savings}."
    )


def _build_reason(slot: dict, rank: int, name: str) -> str:
    rate  = slot["avg_tariff"]
    parts = []
    if rate <= 4.0:
        parts.append("cheapest off-peak slab")
    elif rate <= 6.0:
        parts.append("normal tariff period")
    else:
        parts.append("higher tariff — consider a cheaper slot")
    if slot["savings_vs_now_inr"] > 0:
        parts.append(f"saves ₹{slot['savings_vs_now_inr']} vs running now")
    return f"#{rank + 1} for {name} at {slot['slot_label']}: {', '.join(parts)}."


def _add_minutes_to_str(time_str: str, minutes: int) -> str:
    """Add minutes to HH:MM string, wraps at midnight."""
    h, m  = map(int, time_str.split(":"))
    total = h * 60 + m + minutes
    return f"{(total // 60) % 24:02d}:{total % 60:02d}"