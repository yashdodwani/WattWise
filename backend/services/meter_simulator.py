import random
from datetime import datetime
import pytz
from db.session import SessionLocal
from db.models import Meter, MeterReading

IST = pytz.timezone("Asia/Kolkata")

def generate_reading():
    db = SessionLocal()

    meter = db.query(Meter).first()
    if not meter:
        db.close()
        return

    # simulate realistic home load (0.1 to 0.6 kWh per 15 min)
    energy = round(random.uniform(0.1, 0.6), 3)

    reading = MeterReading(
        meter_id=meter.id,
        timestamp=datetime.now(IST),
        energy_kwh=energy
    )

    db.add(reading)
    db.commit()
    db.close()
