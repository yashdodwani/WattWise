"""
schemas/recommendation.py — WattWise

Pydantic response schema for the /recommendations endpoints.
Used as response_model=List[Recommendation] in api/recommendations.py.
"""

from pydantic import BaseModel


class Recommendation(BaseModel):
    appliance_id           : int
    appliance_name         : str
    can_use_now            : bool
    best_slot              : str    # "HH:MM" — recommended start time (IST)
    estimated_cost_inr     : float  # cost at best slot in ₹
    savings_vs_peak_inr    : float  # savings vs running right now
    recommendation_message : str    # human-readable message
    reason                 : str    # why this slot was picked

    model_config = {"from_attributes": True}