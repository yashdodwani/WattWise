from pydantic import BaseModel
from datetime import datetime
from typing import Optional
from uuid import UUID


class NotificationCreate(BaseModel):
    user_id: UUID
    title: str
    message: str
    type: str = "general"
    priority: Optional[int] = 0


class NotificationResponse(BaseModel):
    id: int
    title: str
    message: str
    type: str
    priority: int
    is_read: bool
    created_at: datetime

    class Config:
        orm_mode = True

