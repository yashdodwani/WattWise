from sqlalchemy.orm import Session
from db.models import User, Meter, Appliance, Tariff
from datetime import time

def seed_data(db: Session):

    # prevent reseeding
    if db.query(User).first():
        return

    user = User(name="Demo User")
    db.add(user)
    db.commit()
    db.refresh(user)

    meter = Meter(user_id=user.id)
    db.add(meter)

    appliances = [
        Appliance(user_id=user.id, name="Washing Machine", power_kw=0.5),
        Appliance(user_id=user.id, name="Air Conditioner", power_kw=1.5),
        Appliance(user_id=user.id, name="Water Heater", power_kw=2.0),
    ]
    db.add_all(appliances)

    tariffs = [
        Tariff(start_time=time(6,0), end_time=time(10,0), price_per_unit=6),
        Tariff(start_time=time(10,0), end_time=time(18,0), price_per_unit=5),
        Tariff(start_time=time(18,0), end_time=time(22,0), price_per_unit=7),
        Tariff(start_time=time(22,0), end_time=time(23,59), price_per_unit=3),
    ]
    db.add_all(tariffs)

    db.commit()
