"""
API endpoints for live meter data.
Placeholder routes for fetching current and historical meter readings.
"""
from fastapi import APIRouter, HTTPException
from typing import List

from ..schemas.meter import MeterReading

router = APIRouter()


@router.get("/current", response_model=MeterReading)
async def get_current_meter_reading():
    """Return the latest meter reading (placeholder)."""
    # Placeholder response
    return MeterReading(timestamp="2026-01-01T00:00:00Z", watts=0.0)


@router.get("/history", response_model=List[MeterReading])
async def get_meter_history(limit: int = 100):
    """Return historical meter readings (placeholder)."""
    return []

