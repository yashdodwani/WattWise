from fastapi import APIRouter, Depends, HTTPException, WebSocket, WebSocketDisconnect
from sqlalchemy.orm import Session
from typing import List
from db.session import get_db
from db.models import Notification
from schemas.notification import NotificationResponse
from api.auth import get_current_user
from services.ws_manager import manager
from services.notification_service import notification_service

router = APIRouter(prefix="/notifications", tags=["Notifications"])


@router.get("", response_model=List[NotificationResponse])
def get_notifications(current_user=Depends(get_current_user), db: Session = Depends(get_db)):
    rows = notification_service.fetch_for_user(current_user.id)
    return rows


@router.post("/read/{notification_id}")
def mark_read(notification_id: int, current_user=Depends(get_current_user), db: Session = Depends(get_db)):
    n = db.query(Notification).filter(Notification.id == notification_id, Notification.user_id == current_user.id).first()
    if not n:
        raise HTTPException(status_code=404, detail="Notification not found")
    n.is_read = True
    db.commit()
    return {"message": "Marked as read", "id": n.id}


@router.websocket_route('/ws/notifications/{user_id}')
async def websocket_endpoint(websocket: WebSocket, user_id: str):
    # Allow unauthenticated websocket connections but in production validate the JWT
    await manager.connect(user_id, websocket)
    try:
        while True:
            data = await websocket.receive_text()
            # Echo or ignore; notifications are pushed from server
            await websocket.send_text(data)
    except WebSocketDisconnect:
        await manager.disconnect(user_id)
