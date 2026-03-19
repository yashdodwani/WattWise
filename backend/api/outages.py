from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from datetime import datetime, timezone
from db.session import get_db
from db.models import Outage, User
from api.auth import get_current_user

router = APIRouter(prefix="/outages", tags=["Outages"])


# ── 1. GET /outages/current ───────────────────────────────────────────────────
@router.get("/current")
def get_current_outage(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Return the active outage for the user's area, or a 'normal' status."""
    user_area = current_user.location

    outage = (
        db.query(Outage)
        .filter(Outage.status == "ACTIVE", Outage.area == user_area)
        .first()
    )

    if not outage:
        return {"status": "normal", "message": "No outages reported in your area"}

    return {
        "area": outage.area,
        "status": "outage",
        "reason": outage.reason,
        "start_time": outage.start_time,
        "expected_restore": outage.expected_restore,
    }


# ── 2. GET /outages/active ────────────────────────────────────────────────────
@router.get("/active")
def get_all_active_outages(
    current_user=Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Return all currently active outages across all areas."""
    outages = db.query(Outage).filter(Outage.status == "ACTIVE").all()

    return [
        {
            "id": o.id,
            "area": o.area,
            "reason": o.reason,
            "expected_restore": (
                o.expected_restore.strftime("%H:%M") if o.expected_restore else None
            ),
        }
        for o in outages
    ]


# ── 3. POST /outages/create ───────────────────────────────────────────────────
@router.post("/create")
def create_outage(
    data: dict,
    current_user=Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Create a new active outage. (Admin / test use)"""
    area = data.get("area")
    reason = data.get("reason")
    expected_restore_raw = data.get("expected_restore")

    if not area or not reason or not expected_restore_raw:
        raise HTTPException(
            status_code=400,
            detail="Fields 'area', 'reason', and 'expected_restore' are required",
        )

    try:
        expected_restore = datetime.fromisoformat(expected_restore_raw)
    except (ValueError, TypeError):
        raise HTTPException(
            status_code=400,
            detail="'expected_restore' must be a valid ISO datetime string (e.g. 2026-03-01T19:30:00)",
        )

    outage = Outage(
        area=area,
        reason=reason,
        status="ACTIVE",
        start_time=datetime.now(timezone.utc),
        expected_restore=expected_restore,
        created_at=datetime.now(timezone.utc),
    )

    db.add(outage)
    db.commit()
    db.refresh(outage)

    return {
        "id": outage.id,
        "area": outage.area,
        "reason": outage.reason,
        "status": outage.status,
        "start_time": outage.start_time,
        "expected_restore": outage.expected_restore,
    }


# ── 4. POST /outages/resolve/{outage_id} ─────────────────────────────────────
@router.post("/resolve/{outage_id}")
def resolve_outage(
    outage_id: int,
    current_user=Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Mark an outage as RESOLVED."""
    outage = db.query(Outage).filter(Outage.id == outage_id).first()

    if not outage:
        raise HTTPException(status_code=404, detail="Outage not found")

    if outage.status == "RESOLVED":
        return {"message": "Outage was already resolved"}

    outage.status = "RESOLVED"
    db.commit()

    return {"message": "Outage resolved successfully"}
