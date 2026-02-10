"""
Pydantic schemas for meter data.
"""
from pydantic import BaseModel
from datetime import datetime


class MeterReading(BaseModel):
    """Schema for a single meter reading."""
    timestamp: datetime
    watts: float

    class Config:
        orm_mode = True

