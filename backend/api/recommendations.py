"""
API endpoints for recommendations: best times and estimated savings.
Placeholder route that returns empty recommendations.
"""
from fastapi import APIRouter
from typing import List

from ..schemas.recommendation import Recommendation

router = APIRouter()


@router.get("/", response_model=List[Recommendation])
async def get_recommendations():
    """Return scheduling recommendations (placeholder)."""
    return []

