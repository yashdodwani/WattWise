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
        Appliance(user_id=user.id, name="Air Conditioner", power_kw=1.45),
        Appliance(user_id=user.id, name="Washing Machine", power_kw=0.5),
        Appliance(user_id=user.id, name="Refrigerator", power_kw=0.12),
        Appliance(user_id=user.id, name="Geyser", power_kw=2.0),
        Appliance(user_id=user.id, name="Television", power_kw=0.08),
        Appliance(user_id=user.id, name="Living Room Lights", power_kw=0.04),
        Appliance(user_id=user.id, name="Ceiling Fan", power_kw=0.07),
        Appliance(user_id=user.id, name="Microwave", power_kw=1.2),
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
