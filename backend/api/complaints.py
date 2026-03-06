from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from sqlalchemy import desc
from db.session import get_db
from db.models import Complaint
from api.auth import get_current_user
from datetime import datetime, timezone

router = APIRouter(prefix="/complaints", tags=["Complaints"])

@router.post("")
def create_complaint(data: dict, current_user=Depends(get_current_user), db: Session = Depends(get_db)):
    complaint = Complaint(
        user_id=current_user.id,
        type=data.get("type"),
        description=data.get("description"),
        status="OPEN",
        created_at=datetime.now(timezone.utc),
    )
    db.add(complaint)
    db.commit()
    db.refresh(complaint)
    return {
        "id": complaint.id,
        "status": complaint.status,
        "message": "Complaint registered successfully"
    }

@router.get("/my")
def get_my_complaints(current_user=Depends(get_current_user), db: Session = Depends(get_db)):
    complaints = db.query(Complaint).filter(Complaint.user_id == current_user.id).order_by(desc(Complaint.created_at)).all()
    return [
        {
            "id": c.id,
            "type": c.type,
            "status": c.status,
            "created_at": c.created_at.date() if c.created_at else None
        }
        for c in complaints
    ]

@router.get("/{complaint_id}")
def get_complaint_details(complaint_id: int, current_user=Depends(get_current_user), db: Session = Depends(get_db)):
    complaint = db.query(Complaint).filter(Complaint.id == complaint_id, Complaint.user_id == current_user.id).first()
    if not complaint:
        raise HTTPException(status_code=404, detail="Complaint not found")
    return {
        "id": complaint.id,
        "type": complaint.type,
        "description": complaint.description,
        "status": complaint.status,
        "created_at": complaint.created_at,
        "resolved_at": complaint.resolved_at,
    }
