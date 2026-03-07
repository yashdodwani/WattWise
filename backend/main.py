from fastapi import FastAPI,Depends
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.orm import Session
from db.session import get_db
from db.session import engine
from db.models import Base
from db.session import SessionLocal
from db.seed import seed_data
import threading
import time
import urllib.request
from api.meter import router as meter_router
from api.appliances import router as appliances_router
from api.tariffs import router as tariff_router
from api.auth import router as auth_router
from api.dashboard import router as dashboard_router
from api.recommendations import router as recommendations_router
from services.meter_simulator import generate_reading
import os
import migrate
from api.billing import router as billing_router
from api.complaints import router as complaints_router
from api.outages import router as outages_router

Base.metadata.create_all(bind=engine)

app = FastAPI(title="wattwise backend")

# Add CORS middleware
# ALLOWED_ORIGINS env var: comma-separated list of origins, or "*" to allow all
_raw_origins = os.getenv(
    "ALLOWED_ORIGINS",
    "http://localhost:8080,http://127.0.0.1:8080,https://smart-flow-uikit.onrender.com"
)
_origins = [o.strip() for o in _raw_origins.split(",")]

app.add_middleware(
    CORSMiddleware,
    allow_origins=_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(meter_router)
app.include_router(tariff_router)
app.include_router(appliances_router)
app.include_router(auth_router)
app.include_router(dashboard_router)
app.include_router(recommendations_router)
app.include_router(billing_router)
app.include_router(complaints_router)
app.include_router(outages_router)
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

    # Optional database migrations: set RUN_MIGRATIONS=1 in env to run
    run_migs = os.getenv("RUN_MIGRATIONS", "0").lower()
    if run_migs in ("1", "true", "yes"):
        try:
            print("🔄 Running migrations (RUN_MIGRATIONS=1)")
            migrate.migrate_users_table()
            migrate.create_otp_table()
            print("✅ Migrations completed")
        except Exception as e:
            print(f"⚠️ Migration failed: {e}")


def meter_loop():
    while True:
        generate_reading()
        time.sleep(15)

@app.on_event("startup")
def start_simulator():
    thread = threading.Thread(target=meter_loop, daemon=True)
    thread.start()


def self_ping_loop():
    """Ping own health endpoint every 9 minutes to prevent Render free-tier spin-down."""
    url = os.getenv("RENDER_EXTERNAL_URL", "").rstrip("/")
    if not url:
        print("ℹ️  RENDER_EXTERNAL_URL not set — self-ping disabled")
        return
    ping_url = f"{url}/"
    while True:
        time.sleep(9 * 60)  # wait 9 minutes
        try:
            with urllib.request.urlopen(ping_url, timeout=10) as resp:
                print(f"🏓 Self-ping OK ({resp.status}): {ping_url}")
        except Exception as e:
            print(f"⚠️  Self-ping failed: {e}")

@app.on_event("startup")
def start_self_ping():
    thread = threading.Thread(target=self_ping_loop, daemon=True)
    thread.start()

