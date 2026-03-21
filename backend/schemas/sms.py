from pydantic import BaseModel
from typing import Optional, List
from datetime import datetime
from uuid import UUID

class SMSLogBase(BaseModel):
    user_id: Optional[UUID] = None
    phone_number: str
    message: str
    status: str = "SENT"

class SMSLogCreate(SMSLogBase):
    pass

class SMSLogResponse(SMSLogBase):
    sms_id: int
    sent_at: datetime

    class Config:
        from_attributes = True

class SMSSendRequest(BaseModel):
    user_id: str  # Changed from int to str to support UUIDs
    phone_number: str
    message: str

class SMSBulkSendRequest(BaseModel):
    category: str
    user_ids: List[str] = []  # Changed from List[int] to List[str] to support UUIDs

class SMSTemplateBase(BaseModel):
    name: str
    message_body: str

class SMSTemplateCreate(SMSTemplateBase):
    pass

class SMSTemplateResponse(SMSTemplateBase):
    id: int
    created_at: datetime

    class Config:
        from_attributes = True
