"""
Helpers to work with 15-minute time slots.
Placeholder functions to snap datetimes to slot boundaries and generate slots.
"""
from datetime import datetime, timedelta
from typing import List


SLOT_MINUTES = 15


def round_down_to_slot(dt: datetime) -> datetime:
    """Round down a datetime to the start of its 15-minute slot."""
    minute_block = (dt.minute // SLOT_MINUTES) * SLOT_MINUTES
    return datetime(dt.year, dt.month, dt.day, dt.hour, minute_block, 0, tzinfo=dt.tzinfo)


def generate_slots(start: datetime, end: datetime) -> List[datetime]:
    """Generate list of slot start times between start (inclusive) and end (exclusive)."""
    slots = []
    cur = round_down_to_slot(start)
    while cur < end:
        slots.append(cur)
        cur += timedelta(minutes=SLOT_MINUTES)
    return slots

