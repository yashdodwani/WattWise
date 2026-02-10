"""
API endpoints for an aggregated dashboard.
Placeholder route aggregating basic stats.
"""
from fastapi import APIRouter

router = APIRouter()


@router.get("/summary")
async def dashboard_summary():
    """Return a basic dashboard summary (placeholder)."""
    return {"active_appliances": 0, "current_consumption_watts": 0.0}

