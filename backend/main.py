"""
FastAPI entry point for the backend.
Starts the FastAPI app and includes API routers from the api package.
"""
from fastapi import FastAPI

# Import routers (placeholders)
from .api import meter, appliances, tariffs, recommendations, dashboard

app = FastAPI(title="WattWise Backend")

# Include routers (each api module should provide `router`)
app.include_router(meter.router, prefix="/api/meter", tags=["meter"])
app.include_router(appliances.router, prefix="/api/appliances", tags=["appliances"])
app.include_router(tariffs.router, prefix="/api/tariffs", tags=["tariffs"])
app.include_router(recommendations.router, prefix="/api/recommendations", tags=["recommendations"])
app.include_router(dashboard.router, prefix="/api/dashboard", tags=["dashboard"])


@app.get("/")
async def root():
    """Health-check/root endpoint."""
    return {"status": "ok", "service": "WattWise Backend"}

