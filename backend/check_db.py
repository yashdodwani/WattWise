import logging
logging.disable(logging.CRITICAL)

from db.session import SessionLocal
from db.models import Appliance, User

db = SessionLocal()
users = db.query(User).all()
for u in users:
    rows = db.query(Appliance).filter(Appliance.user_id == u.id).all()
    print(f"User id={u.id} username={u.username}: {len(rows)} appliances")
    for a in rows:
        print(f"  - {a.id} {a.name} {a.power_kw}kW")
db.close()

