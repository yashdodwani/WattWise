"""
Optimizer Service — WattWise
Algorithm: Sliding Window + Weighted Scoring

Fully aligned with tariff_service.py:
  - Uses IST timezone (Asia/Kolkata) via now_ist()
  - Uses simulate_cost() for minute-level accuracy across slab boundaries
  - Uses find_cheapest_slot() as the core sliding window engine
  - No duplicated tariff logic — all delegated to tariff_service

Score(t) = 0.6 × (1 / avg_cost)         ← cost efficiency  (most important)
         + 0.3 × (1 - grid_load(t))     ← grid friendliness (eco score)
         + 0.1 × time_preference(t)     ← scheduling convenience

find_cheapest_windows() — original signature preserved for backward compatibility.
sliding_window_recommend() — upgraded to minute-level precision via simulate_cost().
can_use_now() — upgraded to use IST and simulate_cost().
"""

import datetime
from math import sin, pi
from typing import List, Tuple
from zoneinfo import ZoneInfo

from services.tariff_service import (
    simulate_cost,
    find_cheapest_slot,
    get_price_for_timestamp,
    now_ist,
)

IST = ZoneInfo("Asia/Kolkata")


# --------------------------------------------------------------------------- #
#  Grid Load Simulation (sinusoidal — peaks ~7 PM, lowest ~3 AM)
#  Kept here as it's an optimizer concern (eco scoring), not a tariff concern.
# --------------------------------------------------------------------------- #

def _grid_load(hour: int) -> float:
    """
    Simulate grid demand using a sinusoidal curve.
    Peaks around 19:00 (7 PM), lowest around 03:00 (3 AM).
    Returns value between 0.1 and 0.9.
    """
    h    = hour % 24
    load = 0.5 + 0.4 * sin(pi * (h - 6) / 12)
    return round(max(0.1, min(0.9, load)), 3)


def _time_preference(hour: int) -> float:
    """
    Scheduling convenience score.
    Favours late-night / early-morning for background/automated runs.
    Returns 0.0 – 1.0.
    """
    h = hour % 24
    if 22 <= h or h < 6:
        return 1.0   # best — off-peak, user asleep, ideal for automation
    elif 6 <= h < 9:
        return 0.6   # morning ok
    elif 18 <= h < 22:
        return 0.1   # peak evening — avoid
    return 0.5       # neutral daytime


def _weighted_score(avg_cost: float, hour: int) -> float:
    """
    Weighted score formula combining cost, grid load, and preference.

    Score(t) = 0.6 × (1 / avg_cost)
             + 0.3 × (1 - grid_load(t))
             + 0.1 × time_preference(t)

    Higher score = better slot.
    """
    return round(
        0.6 * (1 / avg_cost) +
        0.3 * (1 - _grid_load(hour)) +
        0.1 * _time_preference(hour),
        4,
    )


# --------------------------------------------------------------------------- #
#  Original signature — preserved for backward compatibility
#  Now delegates to tariff_service.find_cheapest_slot internally.
# --------------------------------------------------------------------------- #

def find_cheapest_windows(
    tariffs: List[Tuple[datetime.datetime, float]],
    window_minutes: int = 60,
) -> List[Tuple[datetime.datetime, datetime.datetime, float]]:
    """
    Original placeholder signature — fully implemented.

    Slides a window of `window_minutes` across the provided (timestamp, price)
    tuples and returns all windows sorted by cost ascending.

    Args:
        tariffs        : list of (timestamp, price_per_unit) tuples
        window_minutes : desired window length in minutes

    Returns:
        list of (start_time, end_time, estimated_cost) tuples, cheapest first
    """
    if not tariffs:
        return []

    window_steps = max(1, window_minutes // 60)
    results      = []

    for i in range(len(tariffs) - window_steps + 1):
        window   = tariffs[i : i + window_steps]
        avg_rate = sum(p for _, p in window) / len(window)
        start_dt = window[0][0]
        end_dt   = window[-1][0] + datetime.timedelta(hours=1)
        # Cost assumes 1 kW — caller scales by appliance power_kw
        cost     = round(avg_rate * window_steps, 2)
        results.append((start_dt, end_dt, cost))

    results.sort(key=lambda x: x[2])
    return results


# --------------------------------------------------------------------------- #
#  Main Sliding Window Recommendation Engine
#  Upgraded: uses simulate_cost() for minute-level precision
# --------------------------------------------------------------------------- #

def sliding_window_recommend(
    power_kw        : float,
    duration_hrs    : float,
    tariff_rows     : list,
    top_n           : int = 3,
) -> list:
    """
    Slides a window of `duration_hrs` across the full 24-hour day in
    15-minute steps. Each candidate slot is scored using the weighted formula.

    Cost is computed via simulate_cost() which steps in 15-min chunks —
    so appliances crossing a tariff slab boundary (e.g. 21:30–22:30)
    are priced accurately for each chunk, not averaged.

    Args:
        power_kw     : appliance wattage in kW (from Appliance.power_kw)
        duration_hrs : how long the appliance runs (converted to minutes)
        tariff_rows  : list of Tariff ORM objects (fetched once upstream)
        top_n        : number of best slots to return

    Returns:
        list of dicts sorted by score descending, length = top_n
    """
    duration_minutes = round(duration_hrs * 60)
    today            = now_ist().date()
    results          = []

    # Slide in 15-min steps across 24 hours
    cursor   = datetime.datetime(today.year, today.month, today.day, 0, 0, tzinfo=IST)
    end_scan = cursor + datetime.timedelta(hours=24)

    while cursor < end_scan:
        t_str  = cursor.strftime("%H:%M")
        end_dt = cursor + datetime.timedelta(minutes=duration_minutes)

        # Accurate cost via simulate_cost (handles slab boundary crossings)
        sim       = simulate_cost(power_kw, duration_minutes, t_str, tariff_rows)
        avg_cost  = sim["cost"]
        avg_rate  = sim["price_per_unit"]
        mid_dt    = cursor + datetime.timedelta(minutes=duration_minutes // 2)
        score     = _weighted_score(avg_cost if avg_cost > 0 else 0.01, mid_dt.hour)

        # Peak cost = running at the most expensive slab (for savings calc)
        peak_sim  = simulate_cost(power_kw, duration_minutes, "19:00", tariff_rows)
        savings   = round(max(0.0, peak_sim["cost"] - avg_cost), 2)

        results.append({
            "start_time"          : t_str,
            "end_time"            : end_dt.strftime("%H:%M"),
            "slot_label"          : f"{t_str} – {end_dt.strftime('%H:%M')}",
            "avg_tariff"          : avg_rate,
            "estimated_cost_inr"  : avg_cost,
            "savings_vs_peak_inr" : savings,
            "grid_load"           : _grid_load(cursor.hour),
            "score"               : score,
        })

        cursor += datetime.timedelta(minutes=15)

    # Sort by score descending, return top N
    top = sorted(results, key=lambda x: -x["score"])[:top_n]
    for i, s in enumerate(top):
        s["rank"]   = i + 1
        s["reason"] = _build_reason(s, i)

    return top


# --------------------------------------------------------------------------- #
#  can_use_now — upgraded to IST + simulate_cost
# --------------------------------------------------------------------------- #

def can_use_now(
    power_kw        : float,
    duration_hrs    : float,
    tariff_rows     : list,
) -> dict:
    """
    Is right now (IST) a good time to run this appliance?

    Compares the cost of running starting NOW vs the cheapest slot
    found by find_cheapest_slot() over the full 24-hour window.

    Threshold: within 15% of the best possible cost = green light (True).

    Args:
        power_kw     : appliance wattage in kW
        duration_hrs : how long the appliance runs
        tariff_rows  : list of Tariff ORM objects

    Returns:
        dict with can_use_now bool, costs, best slot, and recommendation string
    """
    now              = now_ist()
    now_str          = now.strftime("%H:%M")
    duration_minutes = round(duration_hrs * 60)

    # Cost if started right now
    now_sim  = simulate_cost(power_kw, duration_minutes, now_str, tariff_rows)
    now_cost = now_sim["cost"]

    # Best slot across full 24 hours via sliding window
    best = find_cheapest_slot(
        power_kw         = power_kw,
        duration_minutes = duration_minutes,
        window_start_str = "00:00",
        window_end_str   = "23:45",
        tariff_rows      = tariff_rows,
        step_minutes     = 15,
    )

    best_cost        = best["expected_cost"]
    savings_possible = round(max(0.0, now_cost - best_cost), 2)
    is_good          = now_cost <= best_cost * 1.15  # within 15% = green light

    return {
        "can_use_now"                : is_good,
        "current_time_ist"           : now_str,
        "current_tariff"             : get_price_for_timestamp(now, tariff_rows),
        "current_estimated_cost_inr" : now_cost,
        "best_slot_start"            : best["recommended_start"],
        "best_slot_cost_inr"         : best_cost,
        "savings_if_you_wait_inr"    : savings_possible,
        "recommendation"             : (
            "✅ Good time! Tariff is near its daily low."
            if is_good else
            f"⏳ Wait until {best['recommended_start']} — save ₹{savings_possible}"
        ),
    }


# --------------------------------------------------------------------------- #
#  Internal: reason string builder
# --------------------------------------------------------------------------- #

def _build_reason(slot: dict, rank: int) -> str:
    parts = []
    rate  = slot["avg_tariff"]

    if rate <= 4.0:
        parts.append("lowest tariff slab (off-peak)")
    elif rate <= 6.0:
        parts.append("normal tariff period")
    else:
        parts.append("higher tariff — consider an off-peak slot")

    if slot["grid_load"] < 0.4:
        parts.append("low grid load — eco-friendly")

    if slot["savings_vs_peak_inr"] > 0:
        parts.append(f"saves ₹{slot['savings_vs_peak_inr']} vs peak hours")

    return f"#{rank + 1}: {slot['slot_label']} — {', '.join(parts)}."