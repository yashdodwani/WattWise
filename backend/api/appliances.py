"""
API endpoints to control appliances and scheduling.
Placeholder routes for listing appliances and toggling state.
"""
from fastapi import APIRouter, HTTPException
from typing import List

from ..schemas.appliance import Appliance, ApplianceCommand

router = APIRouter()


@router.get("/", response_model=List[Appliance])
async def list_appliances():
    """Return a list of registered appliances (placeholder)."""
    return []


@router.post("/{appliance_id}/command")
async def control_appliance(appliance_id: int, command: ApplianceCommand):
    """Send an ON/OFF or schedule command to an appliance (placeholder)."""
    return {"appliance_id": appliance_id, "status": "accepted"}

