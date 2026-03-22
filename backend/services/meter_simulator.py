import random
from datetime import datetime
from zoneinfo import ZoneInfo
from db.session import SessionLocal
from db.models import Meter, MeterReading

IST = ZoneInfo("Asia/Kolkata")

def generate_realistic_load():
    """
    Generate realistic current load (kW) based on time of day.
    Morning peak: 6-9 AM
    Evening peak: 6-11 PM
    Low usage: 12-5 AM
    Range: 0.05 kW - 2.5 kW
    """
    now = datetime.now(IST)
    hour = now.hour

    # Base load (always on appliances like fridge, router, etc.)
    load = random.uniform(0.05, 0.2)

    # Morning Peak (6 AM - 9 AM)
    if 6 <= hour < 9:
        load += random.uniform(0.5, 1.5)  # Geyser, Toaster, etc.

    # Evening Peak (6 PM - 11 PM)
    elif 18 <= hour < 23:
        load += random.uniform(0.8, 2.0)  # Lights, TV, AC, Fans

    # Day time (9 AM - 6 PM)
    elif 9 <= hour < 18:
        load += random.uniform(0.1, 0.8)  # Fans, Laptop

    # Late night (11 PM - 5 AM) - Minimal load
    else:
        load += random.uniform(0.0, 0.1)

    # Add random fluctuations
    load += random.normalvariate(0, 0.05)

    # Ensure within bounds
    return max(0.05, min(load, 2.5))

def generate_voltage():
    """
    Return voltage between 210V - 240V with fluctuations.
    """
    return round(random.uniform(210, 240), 1)

def predicted_bill(usage_kwh):
    """
    Calculate bill based on Indian tariff slabs:
    - ₹4 per kWh for first 100 units
    - ₹6 per kWh for 100-300 units
    - ₹7.5 per kWh above 300 units
    """
    if usage_kwh <= 100:
        return usage_kwh * 4
    elif usage_kwh <= 300:
        return (100 * 4) + ((usage_kwh - 100) * 6)
    else:
        return (100 * 4) + (200 * 6) + ((usage_kwh - 300) * 7.5)

def generate_reading():
    db = SessionLocal()

    meter = db.query(Meter).first()
    if not meter:
        db.close()
        return

    # simulate realistic home load based on time of day
    current_load_kw = generate_realistic_load()

    # Convert kW to kWh for 15-second interval (simulator loop)
    # Energy (kWh) = Power (kW) * Time (hours)
    # Time is 15 seconds = 15/3600 hours
    energy = round(current_load_kw * (15 / 3600), 5)

    reading = MeterReading(
        meter_id=meter.id,
        timestamp=datetime.now(IST),
        energy_kwh=energy
    )

    db.add(reading)
    db.commit()
    db.close()

def generate_daily_consumption(meter_id, date):
    """
    Generate total energy consumption for a day for a given meter.
    """
    # Assuming 96 intervals of 15 minutes in a day
    total_energy = sum(generate_realistic_load() * 0.25 for _ in range(96))

    # Create a MeterReading object for daily consumption
    daily_reading = MeterReading(
        meter_id=meter_id,
        timestamp=date,
        energy_kwh=round(total_energy, 3)
    )

    db = SessionLocal()
    db.add(daily_reading)
    db.commit()
    db.close()

def generate_live_consumption_series(meter_id, duration_minutes):
    """
    Generate a time series of energy consumption readings for a given duration.
    """
    series = []
    intervals = duration_minutes // 15  # 15-minute intervals

    for _ in range(intervals):
        load_kw = generate_realistic_load()
        energy_kwh = round(load_kw * 0.25, 3)
        timestamp = datetime.now(IST)

        reading = MeterReading(
            meter_id=meter_id,
            timestamp=timestamp,
            energy_kwh=energy_kwh
        )
        series.append(reading)

    db = SessionLocal()
    db.add_all(series)
    db.commit()
    db.close()
