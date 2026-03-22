import random
from datetime import datetime
from zoneinfo import ZoneInfo
from db.session import SessionLocal
from db.models import Meter, MeterReading, Appliance

IST = ZoneInfo("Asia/Kolkata")

def generate_reading():
    db = SessionLocal()

    meters = db.query(Meter).all()
    if not meters:
        db.close()
        return

    readings = []
    current_time = datetime.now(IST)

    for meter in meters:
        # Get user's active appliances to calculate real load
        appliances = db.query(Appliance).filter(Appliance.user_id == meter.user_id).all()
        
        active_load_kw = 0.0
        
        # Base load logic:
        # 1. Random fluctuation (50W - 200W) for unlisted devices
        # 2. Standby/Leakage load relative to appliance power rating (1% of power_kw)
        appliance_standby_load = sum(app.power_kw * 0.01 for app in appliances)
        
        base_load_kw = random.uniform(0.05, 0.2) + appliance_standby_load
        
        for app in appliances:
            if app.is_on:
                # Add full power rating if ON
                active_load_kw += app.power_kw
            else:
                # Add tiny phantom load if OFF (5W)
                active_load_kw += 0.005

        total_load_kw = base_load_kw + active_load_kw
        
        # Add some noise (±10%)
        total_load_kw *= random.uniform(0.9, 1.1)

        # Calculate energy for 15 minutes (0.25 hours)
        energy_kwh = round(total_load_kw * 0.25, 3)

        readings.append(MeterReading(
            meter_id=meter.id,
            timestamp=current_time,
            energy_kwh=energy_kwh
        ))

    db.add_all(readings)
    db.commit()
    db.close()
