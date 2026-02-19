"""
Helpers to calculate cost and CO2 savings estimates.
Placeholder functions for computing cost given consumption and tariffs.
"""
from typing import List, Tuple


def estimate_cost(consumption_kwh: float, price_per_kwh: float) -> float:
    """Estimate cost for given consumption and price (placeholder)."""
    return consumption_kwh * price_per_kwh


def estimate_co2(consumption_kwh: float, grams_per_kwh: float = 400.0) -> float:
    """Estimate CO2 emissions in grams (placeholder)."""
    return consumption_kwh * grams_per_kwh
