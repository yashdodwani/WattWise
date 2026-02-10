"""
Pydantic schemas for appliances and commands.
"""
from pydantic import BaseModel
from typing import Optional


class Appliance(BaseModel):
    id: int
    user_id: int
    name: str
    power_watts: float
    is_on: bool

    class Config:
        orm_mode = True


class ApplianceCommand(BaseModel):
    """Command to control an appliance."""
    action: str  # e.g., "on", "off", "schedule"
    start_time: Optional[str] = None
    end_time: Optional[str] = None

