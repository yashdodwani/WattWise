from fastapi import FastAPI,Depends
from sqlalchemy.orm import Session
from db.session import get_db
from db.session import engine
from db.models import Base
from db.session import SessionLocal
from db.seed import seed_data
import threading
import time
from api.meter import router as meter_router
from api.appliances import router as appliances_router

from services.meter_simulator import generate_reading

Base.metadata.create_all(bind=engine)

app = FastAPI(title="wattwise backend")
app.include_router(meter_router)

app.include_router(appliances_router)
@app.get("/")
def health_check():
    return {"status":"wattwise backend is running"}

@app.get("/db-check")
def db_check(db: Session = Depends(get_db)):
    return {"db": "connected"}

@app.on_event("startup")
def startup_event():
    db = SessionLocal()
    seed_data(db)
    db.close()

def meter_loop():
    while True:
        generate_reading()
        time.sleep(15)  # demo speed (15 sec instead of 15 min)

@app.on_event("startup")
def start_simulator():
    thread = threading.Thread(target=meter_loop, daemon=True)
    thread.start()