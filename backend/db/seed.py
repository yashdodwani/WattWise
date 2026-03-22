from sqlalchemy.orm import Session
from .models import User, Meter, Appliance, Tariff
from datetime import time

DEFAULT_APPLIANCES = [
    {"name": "Air Conditioner",   "power_kw": 1.45},
    {"name": "Washing Machine",   "power_kw": 0.5},
    {"name": "Refrigerator",      "power_kw": 0.12},
    {"name": "Geyser",            "power_kw": 2.0},
    {"name": "Television",        "power_kw": 0.08},
    {"name": "Living Room Lights","power_kw": 0.04},
    {"name": "Ceiling Fan",       "power_kw": 0.07},
    {"name": "Microwave",         "power_kw": 1.2},
]

def seed_appliances_for_user(db: Session, user_id: int):
    """Create default appliances + meter for a user if they don't have any yet."""
    # Create a meter for the user if none exists
    meter_exists = db.query(Meter).filter(Meter.user_id == user_id).first()
    if not meter_exists:
        db.add(Meter(user_id=user_id))
        db.commit()

    # We no longer seed default appliances as users add them manually
    # existing = db.query(Appliance).filter(Appliance.user_id == user_id).first()
    # if existing:
    #     return  # already seeded

    # for a in DEFAULT_APPLIANCES:
    #     db.add(Appliance(user_id=user_id, name=a["name"], power_kw=a["power_kw"]))

    # db.commit()

def seed_data(db: Session):
    # prevent reseeding
    if db.query(User).first():
        return

    user = User(name="Demo User")
    db.add(user)
    db.commit()
    db.refresh(user)

    seed_appliances_for_user(db, user.id)

    tariffs = [
        Tariff(start_time=time(6,0),  end_time=time(10,0), price_per_unit=6),
        Tariff(start_time=time(10,0), end_time=time(18,0), price_per_unit=5),
        Tariff(start_time=time(18,0), end_time=time(22,0), price_per_unit=7),
        Tariff(start_time=time(22,0), end_time=time(23,59), price_per_unit=3),
    ]
    db.add_all(tariffs)
    db.commit()
