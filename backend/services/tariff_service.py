"""
tariff_service.py — WattWise Tariff Business Logic

Handles all tariff calculations:
  - Matching a timestamp to the correct tariff slab
  - Today's bill from meter readings
  - Cost simulation for a given appliance run
  - Cheapest time slot finder (Sliding Window algorithm)

Timezone: Asia/Kolkata (IST, UTC+5:30)
Midnight-crossing slabs (e.g. 22:00–06:00) are handled explicitly.
DB queries for tariffs are done once per request and passed around
to avoid repeated hits.
"""

import datetime
from zoneinfo import ZoneInfo

IST = ZoneInfo("Asia/Kolkata")


# --------------------------------------------------------------------------- #
#  TIMEZONE HELPER
# --------------------------------------------------------------------------- #

def now_ist() -> datetime.datetime:
    """Return current datetime in IST."""
    return datetime.datetime.now(tz=IST)


# --------------------------------------------------------------------------- #
#  CORE: Match a time to a tariff slab
# --------------------------------------------------------------------------- #

def get_price_for_timestamp(
    dt: datetime.datetime,
    tariff_rows: list,
) -> float:
    """
    Given a datetime and list of Tariff ORM objects,
    return the price_per_unit for that moment.

    Handles overnight slabs (e.g. start=22:00, end=06:00)
    where start_time > end_time.

    Args:
        dt          : datetime (naive or aware). Only time part is used.
        tariff_rows : list of Tariff ORM objects from DB.

    Returns:
        float price_per_unit. Falls back to 6.0 if no slab matches.
    """
    # Normalise to IST time-only
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=IST)
    else:
        dt = dt.astimezone(IST)

    t = dt.time()

    for row in tariff_rows:
        s = row.start_time
        e = row.end_time

        if s < e:
            # Normal slab: 06:00 – 22:00
            if s <= t < e:
                return row.price_per_unit
        else:
            # Overnight slab: 22:00 – 06:00 (crosses midnight)
            if t >= s or t < e:
                return row.price_per_unit

    return 6.0  # safe default if DB has no matching slab


# --------------------------------------------------------------------------- #
#  FEATURE 1 — Current tariff
# --------------------------------------------------------------------------- #

def get_current_tariff(tariff_rows: list) -> dict:
    """
    Return tariff slab active right now in IST.

    Returns:
        {"current_price": float, "time_range": "HH:MM - HH:MM"}
    """
    now = now_ist()
    t   = now.time()

    for row in tariff_rows:
        s = row.start_time
        e = row.end_time

        matched = (s < e and s <= t < e) or (s >= e and (t >= s or t < e))
        if matched:
            return {
                "current_price": row.price_per_unit,
                "time_range"   : f"{s.strftime('%H:%M')} - {e.strftime('%H:%M')}",
            }

    return {"current_price": 6.0, "time_range": "unknown"}


# --------------------------------------------------------------------------- #
#  FEATURE 2 — Full schedule
# --------------------------------------------------------------------------- #

def get_full_schedule(tariff_rows: list) -> list:
    """
    Return all tariff slabs ordered by start_time.
    Overnight slab (start > end) is placed last naturally.

    Returns:
        list of {"start": "HH:MM", "end": "HH:MM", "price": float}
    """
    sorted_rows = sorted(
        tariff_rows,
        key=lambda r: (r.start_time >= datetime.time(6, 0), r.start_time),
    )
    return [
        {
            "start": row.start_time.strftime("%H:%M"),
            "end"  : row.end_time.strftime("%H:%M"),
            "price": row.price_per_unit,
        }
        for row in sorted_rows
    ]


# --------------------------------------------------------------------------- #
#  FEATURE 4 — Today's bill
# --------------------------------------------------------------------------- #

def calculate_today_cost(meter_readings: list, tariff_rows: list) -> dict:
    """
    Sum up cost of all meter readings from today (IST).

    For each reading:
        cost += energy_kwh × tariff_price_at(reading.timestamp)

    Args:
        meter_readings : list of MeterReading ORM objects (today's only).
        tariff_rows    : list of Tariff ORM objects.

    Returns:
        {"today_kwh": float, "today_cost": float}
    """
    total_kwh  = 0.0
    total_cost = 0.0

    for reading in meter_readings:
        price       = get_price_for_timestamp(reading.timestamp, tariff_rows)
        total_kwh  += reading.energy_kwh
        total_cost += reading.energy_kwh * price

    return {
        "today_kwh" : round(total_kwh, 3),
        "today_cost": round(total_cost, 2),
    }


# --------------------------------------------------------------------------- #
#  FEATURE 5 — Cost simulation
# --------------------------------------------------------------------------- #

def simulate_cost(
    power_kw: float,
    duration_minutes: int,
    start_time_str: str,      # "HH:MM"
    tariff_rows: list,
) -> dict:
    """
    Simulate cost of running an appliance at a specific start time.

    Uses today's date in IST with the given start_time to build a datetime,
    then looks up the tariff. Handles appliances that run across slab boundaries
    by stepping in 15-minute intervals.

    Args:
        power_kw         : appliance wattage in kW
        duration_minutes : how long it runs
        start_time_str   : "HH:MM" in IST
        tariff_rows      : list of Tariff ORM objects

    Returns:
        {"energy_used": float, "cost": float, "price_per_unit": float}
    """
    h, m     = map(int, start_time_str.split(":"))
    today    = datetime.datetime.now(tz=IST).date()
    start_dt = datetime.datetime(today.year, today.month, today.day, h, m, tzinfo=IST)

    # Step through in 15-min intervals for accuracy across slab boundaries
    step_minutes = 15
    total_cost   = 0.0
    elapsed      = 0
    last_price   = 6.0

    while elapsed < duration_minutes:
        chunk   = min(step_minutes, duration_minutes - elapsed)
        current = start_dt + datetime.timedelta(minutes=elapsed)
        price   = get_price_for_timestamp(current, tariff_rows)
        energy  = power_kw * (chunk / 60)
        total_cost += energy * price
        last_price  = price
        elapsed    += chunk

    energy_used = round(power_kw * duration_minutes / 60, 3)

    # Effective average price
    avg_price = round(total_cost / energy_used, 2) if energy_used > 0 else last_price

    return {
        "energy_used"    : energy_used,
        "cost"           : round(total_cost, 2),
        "price_per_unit" : avg_price,
    }


# --------------------------------------------------------------------------- #
#  FEATURE 6 — Cheapest slot finder (Sliding Window)
# --------------------------------------------------------------------------- #

def find_cheapest_slot(
    power_kw: float,
    duration_minutes: int,
    window_start_str: str,   # "HH:MM"
    window_end_str: str,     # "HH:MM"
    tariff_rows: list,
    step_minutes: int = 15,  # granularity of sliding window
) -> dict:
    """
    Sliding Window algorithm to find the cheapest continuous time slot
    within a given search window.

    The window itself can cross midnight (e.g. 18:00 – 06:00).
    Each candidate start is stepped by `step_minutes`.
    Each candidate is evaluated by simulate_cost().

    Args:
        power_kw          : appliance wattage in kW
        duration_minutes  : appliance run time in minutes
        window_start_str  : search window start "HH:MM"
        window_end_str    : search window end "HH:MM"
        tariff_rows       : list of Tariff ORM objects
        step_minutes      : how many minutes to slide each step (default 15)

    Returns:
        {"recommended_start": "HH:MM", "expected_cost": float, "savings_vs_now": float}
    """
    today = datetime.datetime.now(tz=IST).date()

    def parse_dt(time_str: str, base_date) -> datetime.datetime:
        h, m = map(int, time_str.split(":"))
        return datetime.datetime(base_date.year, base_date.month, base_date.day, h, m, tzinfo=IST)

    win_start = parse_dt(window_start_str, today)
    win_end   = parse_dt(window_end_str, today)

    # Handle overnight window (e.g. 18:00 – 06:00 next day)
    if win_end <= win_start:
        win_end += datetime.timedelta(days=1)

    # Build all candidate start times within the window
    candidates = []
    cursor = win_start
    while cursor + datetime.timedelta(minutes=duration_minutes) <= win_end:
        candidates.append(cursor)
        cursor += datetime.timedelta(minutes=step_minutes)

    if not candidates:
        return {
            "recommended_start": window_start_str,
            "expected_cost"    : 0.0,
            "savings_vs_now"   : 0.0,
            "message"          : "Window too small for this duration.",
        }

    # Evaluate cost for each candidate
    best_start = None
    best_cost  = float("inf")

    for candidate in candidates:
        time_str = candidate.strftime("%H:%M")
        result   = simulate_cost(power_kw, duration_minutes, time_str, tariff_rows)
        if result["cost"] < best_cost:
            best_cost  = result["cost"]
            best_start = candidate

    # Cost if run right now (for savings comparison)
    now_str      = now_ist().strftime("%H:%M")
    now_result   = simulate_cost(power_kw, duration_minutes, now_str, tariff_rows)
    savings      = round(max(0.0, now_result["cost"] - best_cost), 2)

    return {
        "recommended_start": best_start.strftime("%H:%M"),
        "expected_cost"    : round(best_cost, 2),
        "savings_vs_now"   : savings,
    }