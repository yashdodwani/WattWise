from pydantic import BaseModel
from typing import Optional, List
from datetime import datetime
from uuid import UUID

class TransactionBase(BaseModel):
    user_id: UUID
    amount: float
    payment_method: str
    status: str = "SUCCESS"

class TransactionCreate(TransactionBase):
    pass

class TransactionResponse(TransactionBase):
    transaction_id: int
    created_at: datetime

    class Config:
        from_attributes = True

class RevenueSummary(BaseModel):
    total_revenue: float
    pending_revenue: float
    average_bill_amount: float
    highest_payment: float

class RevenueByState(BaseModel):
    state: str
    revenue: float

class RevenueMonthly(BaseModel):
    month: str
    revenue: float

class PaymentMethodDistribution(BaseModel):
    method: str
    count: int

class RechargeDistribution(BaseModel):
    range: str
    count: int

