# dashboard.py — FastAPI router for Smart Metering Dashboard
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

# Import database session
from backend.db.session import get_db

# Import your service functions
from backend.services import get_meter_data, get_appliance_data
from backend.tariff_service import get_current_tariff, calculate_today_cost, find_cheapest_slot

# Import ORM model for tariffs
from backend.db.models import Tariff

dashboard_router = APIRouter(prefix="/dashboard", tags=["dashboard"])

@dashboard_router.get("/summary")
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
        # ---------------- Fetch data ---------------- #
        meter_data = get_meter_data(db)          # Example: [{'timestamp': ..., 'consumption': ...}]
        appliance_data = get_appliance_data(db)  # Example: [{'appliance_name': 'AC', 'consumption': ...}]
        tariff_rows = db.query(Tariff).all()     # Fetch all tariff slabs from DB

        # ---------------- Total Consumption ---------------- #
        total_consumption = sum(entry['consumption'] for entry in meter_data)

        # Appliance-wise consumption
        appliance_summary = {}
        for entry in appliance_data:
            appliance = entry['appliance_name']
            appliance_summary[appliance] = appliance_summary.get(appliance, 0) + entry['consumption']

        # ---------------- Today's Cost ---------------- #
        today_cost_info = calculate_today_cost(meter_data, tariff_rows)

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
        except Exception:
            cheapest_slot = {"message": "Unable to calculate cheapest slot"}

        # ---------------- Response ---------------- #
        return {
            "total_consumption": total_consumption,
            "appliance_summary": appliance_summary,
            "today_kwh": today_cost_info["today_kwh"],
            "today_cost": today_cost_info["today_cost"],
            "current_tariff": current_tariff,
            "cheapest_slot_example": cheapest_slot
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

