"""
API endpoints for time-of-day tariffs.
Placeholder routes for retrieving tariff schedules.
"""
from fastapi import APIRouter
from typing import List

router = APIRouter()


@router.get("/", response_model=List[dict])
async def get_tariffs():
    """Return tariff schedule (placeholder)."""
    return []

