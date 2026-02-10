"""
Pydantic schemas for recommendations and savings estimates.
"""
from pydantic import BaseModel
from datetime import datetime


class Recommendation(BaseModel):
    start: datetime
    end: datetime
    estimated_savings_eur: float
    estimated_co2_grams: float

    class Config:
        orm_mode = True

