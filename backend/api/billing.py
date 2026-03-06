from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from sqlalchemy import desc
from db.session import get_db
from db.models import Bill, MeterReading, Meter
from api.auth import get_current_user
from datetime import datetime

router = APIRouter(prefix="/billing", tags=["Billing"])


@router.get("/current")
def get_current_bill(current_user=Depends(get_current_user), db: Session = Depends(get_db)):
    bill = db.query(Bill).filter(Bill.user_id == current_user.id, Bill.status == "unpaid").order_by(desc(Bill.created_at)).first()
    if bill:
        return {
            "bill_id": bill.id,
            "units": bill.units,
            "amount": bill.amount,
            "due_date": bill.due_date.date() if bill.due_date else None,
            "status": bill.status,
        }
    # Simulate bill if none exists
    meter = db.query(Meter).filter(Meter.user_id == current_user.id).first()
    if not meter:
        raise HTTPException(status_code=404, detail="No meter found for user")
    readings = db.query(MeterReading).filter(MeterReading.meter_id == meter.id).all()
    units = sum(r.energy_kwh for r in readings)
    amount = round(units * 7, 2)
    due_date = datetime.now().date()
    return {
        "bill_id": None,
        "units": round(units, 2),
        "amount": amount,
        "due_date": due_date,
        "status": "unpaid",
    }


@router.get("/history")
def get_billing_history(current_user=Depends(get_current_user), db: Session = Depends(get_db)):
    bills = db.query(Bill).filter(Bill.user_id == current_user.id).order_by(desc(Bill.created_at)).all()
    history = []
    for bill in bills:
        month = bill.created_at.strftime("%b %Y") if bill.created_at else None
        history.append({
            "month": month,
            "units": bill.units,
            "amount": bill.amount,
            "status": bill.status,
        })
    return history


@router.post("/pay/{bill_id}")
def pay_bill(bill_id: int, current_user=Depends(get_current_user), db: Session = Depends(get_db)):
    bill = db.query(Bill).filter(Bill.id == bill_id, Bill.user_id == current_user.id).first()
    if not bill:
        raise HTTPException(status_code=404, detail="Bill not found")
    if bill.status == "paid":
        raise HTTPException(status_code=400, detail="Bill already paid")
    bill.status = "paid"
    db.commit()
    return {
        "message": "Payment successful",
        "bill_id": bill.id,
        "status": bill.status,
    }
