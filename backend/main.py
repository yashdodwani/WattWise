from fastapi import FastAPI,Depends
from fastapi.middleware.cors import CORSMiddleware
from fastapi.openapi.models import SecurityScheme
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
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
from importlib import import_module
migrate = import_module('migrate')
from api.billing import router as billing_router
from api.complaints import router as complaints_router
from api.outages import router as outages_router
from api.chatbot import router as chatbot_router
from api.notifications import router as notifications_router
from api.revenue import router as revenue_router
from api.sms import router as sms_router
from services.notification_service import notification_service
from services import ws_manager
import asyncio

Base.metadata.create_all(bind=engine)

app = FastAPI(
    title="WattWise Backend API",
    description="Smart Electricity Management Platform",
    version="1.0.0",
)

# Configure Bearer token authentication for Swagger UI
security = HTTPBearer()

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
app.include_router(chatbot_router)
app.include_router(notifications_router)
app.include_router(revenue_router)
app.include_router(sms_router)

# Add Bearer token authentication scheme to OpenAPI for Swagger UI
def custom_openapi():
    if app.openapi_schema:
        return app.openapi_schema

    from fastapi.openapi.utils import get_openapi

    openapi_schema = get_openapi(
        title="WattWise Backend API",
        version="1.0.0",
        description="Smart Electricity Management Platform",
        routes=app.routes,
    )

    # Add Bearer token security scheme
    openapi_schema["components"]["securitySchemes"] = {
        "BearerAuth": {
            "type": "http",
            "scheme": "bearer",
            "bearerFormat": "JWT",
            "description": "Enter your JWT token obtained from /auth/login or /auth/register"
        }
    }

    # Apply security globally to all endpoints (except auth endpoints)
    for path, path_item in openapi_schema["paths"].items():
        # Skip auth endpoints (login, register, otp, forgot-password, reset-password)
        if "/auth/" in path and any(endpoint in path for endpoint in ["login", "register", "otp", "forgot-password", "reset-password"]):
            continue

        for method in path_item:
            if method in ["get", "post", "put", "delete", "patch"]:
                if "security" not in path_item[method]:
                    path_item[method]["security"] = [{"BearerAuth": []}]

    app.openapi_schema = openapi_schema
    return app.openapi_schema

app.openapi = custom_openapi

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

    # start background notification checks
    try:
        loop = asyncio.get_event_loop()
        loop.create_task(notification_service.run_periodic_checks())
    except RuntimeError:
        # If no running loop (e.g., during tests), ignore
        pass


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
