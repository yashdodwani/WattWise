import asyncio
from datetime import datetime, timedelta
from typing import List
from db.session import SessionLocal
from db.models import Notification, Bill, ApplianceUsage, Appliance
from services.ws_manager import manager

CHECK_INTERVAL = 60  # seconds

class NotificationService:
    def __init__(self):
        self.db_factory = SessionLocal
        self.loop = asyncio.get_event_loop()

    def create_notification(self, user_id: str, title: str, message: str, type: str = "general", priority: int = 0) -> Notification:
        db = self.db_factory()
        notif = Notification(
            user_id=user_id,
            title=title,
            message=message,
            type=type,
            priority=priority,
            is_read=False,
            created_at=datetime.now(),
        )
        db.add(notif)
        db.commit()
        db.refresh(notif)
        db.close()

        # Send via websocket if connected (fire-and-forget)
        try:
            asyncio.create_task(manager.send_personal_message(user_id, {
                "id": notif.id,
                "title": notif.title,
                "message": notif.message,
                "type": notif.type,
                "priority": notif.priority,
                "is_read": notif.is_read,
                "created_at": notif.created_at.isoformat(),
            }))
        except RuntimeError:
            # event loop not running
            pass

        return notif

    def mark_as_read(self, notif_id: int) -> bool:
        db = self.db_factory()
        n = db.query(Notification).filter(Notification.id == notif_id).first()
        if not n:
            db.close()
            return False
        n.is_read = True
        db.commit()
        db.close()
        return True

    def fetch_for_user(self, user_id: str) -> List[Notification]:
        db = self.db_factory()
        rows = db.query(Notification).filter(Notification.user_id == user_id).order_by(Notification.created_at.desc()).all()
        db.close()
        return rows

    # Background checks
    def _check_bill_due(self):
        db = self.db_factory()
        now = datetime.now()
        threshold = now + timedelta(days=3)
        bills = db.query(Bill).filter(Bill.status == "unpaid").all()
        for b in bills:
            if b.due_date and now <= b.due_date <= threshold:
                days = (b.due_date.date() - now.date()).days
                title = "Bill Due Reminder"
                message = f"Your bill (ID {b.id}) is due in {days} day(s)."
                # avoid duplicate notifications: naive check
                exists = db.query(Notification).filter(Notification.user_id == b.user_id, Notification.title == title, Notification.message.like(f"%{b.id}%")).first()
                if not exists:
                    self.create_notification(b.user_id, title, message, type="bill", priority=1)
        db.close()

    def _check_appliance_usage(self):
        db = self.db_factory()
        # Example rule: any appliance usage record with energy_kwh > threshold triggers alert
        THRESHOLD_KWH = 5.0  # arbitrary large usage in one session
        usages = db.query(ApplianceUsage).filter(ApplianceUsage.energy_kwh >= THRESHOLD_KWH).all()
        for u in usages:
            title = "High Appliance Usage"
            message = f"Your appliance (ID {u.appliance_id}) recorded high usage: {u.energy_kwh} kWh."
            exists = db.query(Notification).filter(Notification.user_id == u.appliance_id, Notification.title == title, Notification.message.like(f"%{u.appliance_id}%")).first()
            if not exists:
                # need to map appliance to user
                app = db.query(Appliance).filter(Appliance.id == u.appliance_id).first()
                if app:
                    self.create_notification(app.user_id, title, message, type="appliance", priority=1)
        db.close()

    def _check_smart_recommendations(self):
        db = self.db_factory()
        # Example: send recommendation if appliance has been ON for > 5 hours
        five_hours_ago = datetime.now() - timedelta(hours=5)
        appliances = db.query(Appliance).filter(Appliance.is_on == True, Appliance.last_started_at <= five_hours_ago).all()
        for a in appliances:
            title = "Smart Recommendation"
            message = f"{a.name} has been running for a long time. Consider switching it off to save energy."
            exists = db.query(Notification).filter(Notification.user_id == a.user_id, Notification.title == title, Notification.message.like(f"%{a.name}%")).first()
            if not exists:
                self.create_notification(a.user_id, title, message, type="recommendation", priority=0)
        db.close()

    async def run_periodic_checks(self):
        while True:
            try:
                self._check_bill_due()
                self._check_appliance_usage()
                self._check_smart_recommendations()
            except Exception:
                pass
            await asyncio.sleep(CHECK_INTERVAL)


notification_service = NotificationService()
