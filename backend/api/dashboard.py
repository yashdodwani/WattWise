# dashboard.py — FastAPI router for Smart Metering Dashboard
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo

# Import database session and models
from db.session import get_db
from db.models import Appliance, MeterReading, Tariff, ApplianceUsage

# Import service functions (these exist in your codebase)
from services.tariff_service import (
    get_current_tariff, 
    calculate_today_cost, 
    find_cheapest_slot,
    now_ist,
    get_price_for_timestamp
)
from services.meter_simulator import generate_reading

# Create router (make sure variable name matches import in main.py)
router = APIRouter(prefix="/dashboard", tags=["dashboard"])  # Changed to 'router'

@router.get("/summary")  # Using 'router' not 'dashboard_router'
def dashboard_summary(db: Session = Depends(get_db)):
    """
    Returns aggregated data for Smart Metering Dashboard:
    - Total consumption
    - Appliance-wise usage
    - Cost based on today's tariff
    - Current tariff info
    - Suggested cheapest slot for an example appliance
    """
    try:
        now = now_ist()
        today_start = datetime(now.year, now.month, now.day, 0, 0, 0, tzinfo=ZoneInfo("Asia/Kolkata"))
        
        # ---------------- Fetch data ---------------- #
        # Get today's meter readings
        meter_readings = db.query(MeterReading).filter(
            MeterReading.timestamp >= today_start
        ).all()
        
        # Get all appliances
        appliances = db.query(Appliance).all()
        
        # Get today's appliance usage
        appliance_usage = db.query(ApplianceUsage).filter(
            ApplianceUsage.start_time >= today_start
        ).all()
        
        tariff_rows = db.query(Tariff).all()     # Fetch all tariff slabs from DB

        # ---------------- Total Consumption ---------------- #
        total_consumption = sum(reading.energy_kwh for reading in meter_readings)

        # ---------------- Appliance-wise consumption ---------------- #
        appliance_summary = {}
        for usage in appliance_usage:
            appliance = db.query(Appliance).filter(Appliance.id == usage.appliance_id).first()
            if appliance:
                name = appliance.name
                appliance_summary[name] = appliance_summary.get(name, 0) + usage.energy_kwh

        # ---------------- Today's Cost ---------------- #
        today_cost_info = calculate_today_cost(meter_readings, tariff_rows)

        # ---------------- Current Tariff ---------------- #
        current_tariff = get_current_tariff(tariff_rows)

        # ---------------- Cheapest Slot Suggestion ---------------- #
        # Example: AC appliance 1.5 kW for 60 min, search window 18:00-23:00
        try:
            cheapest_slot = find_cheapest_slot(
                power_kw=1.5,
                duration_minutes=60,
                window_start_str="18:00",
                window_end_str="23:00",
                tariff_rows=tariff_rows
            )
        except Exception as e:
            cheapest_slot = {"message": f"Unable to calculate cheapest slot: {str(e)}"}

        # ---------------- Response ---------------- #
        return {
            "status": "success",
            "total_consumption_kwh": round(total_consumption, 3),
            "appliance_summary": appliance_summary,
            "today_kwh": today_cost_info["today_kwh"],
            "today_cost_inr": today_cost_info["today_cost"],
            "current_tariff": current_tariff,
            "cheapest_slot_example": cheapest_slot,
            "timestamp": now.isoformat()
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

