"""
pytest tests for /notifications routes
Covers:
  GET  /notifications          – list notifications for the current user
  POST /notifications/read/{id} – mark a notification as read
"""

import sys
import os

# Make sure the backend package is importable when running from the tests/ dir
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from db.models import Base, User, Notification
from db.session import get_db
from utils.security import hash_password, create_access_token
from main import app
import services.notification_service as _ns_module

# ---------------------------------------------------------------------------
# In-memory SQLite test database
# ---------------------------------------------------------------------------
TEST_DATABASE_URL = "sqlite:///./test_notifications.db"

engine = create_engine(
    TEST_DATABASE_URL, connect_args={"check_same_thread": False}
)
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


def override_get_db():
    db = TestingSessionLocal()
    try:
        yield db
    finally:
        db.close()


# Apply the override before any request is made
app.dependency_overrides[get_db] = override_get_db

# Also patch the notification_service so fetch_for_user uses the test DB
_ns_module.notification_service.db_factory = TestingSessionLocal


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture(scope="module", autouse=True)
def setup_db():
    """Create all tables once for the whole module, drop them after."""
    Base.metadata.create_all(bind=engine)
    yield
    Base.metadata.drop_all(bind=engine)
    engine.dispose()
    # Remove the SQLite file created during tests
    db_file = os.path.join(os.path.dirname(__file__), "..", "test_notifications.db")
    try:
        if os.path.exists(db_file):
            os.remove(db_file)
    except PermissionError:
        pass  # file still locked on Windows; leave it – it will be overwritten next run


@pytest.fixture(scope="module")
def db():
    """Return a module-scoped DB session for seeding data."""
    session = TestingSessionLocal()
    yield session
    session.close()


@pytest.fixture(scope="module")
def test_user(db):
    """Create and persist a test user (ravikumar / mutkut)."""
    user = User(
        name="Ravi Kumar",
        username="ravikumar",
        password_hash=hash_password("mutkut"),
        phone_number="9876543210",
        consumer_number="1234567890",
        is_active=True,
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    return user


@pytest.fixture(scope="module")
def auth_headers(test_user):
    """Return Authorization headers carrying a valid JWT for test_user."""
    token = create_access_token(test_user.id, test_user.username)
    return {"Authorization": f"Bearer {token}"}


@pytest.fixture(scope="module")
def seed_notifications(db, test_user):
    """Seed two notifications for the test user and return them."""
    n1 = Notification(
        user_id=test_user.id,
        title="Bill Due",
        message="Your electricity bill is due in 2 days.",
        type="bill",
        priority=1,
        is_read=False,
    )
    n2 = Notification(
        user_id=test_user.id,
        title="High Usage Alert",
        message="Your AC has been running for 8 hours.",
        type="appliance",
        priority=2,
        is_read=False,
    )
    db.add_all([n1, n2])
    db.commit()
    db.refresh(n1)
    db.refresh(n2)
    return [n1, n2]


@pytest.fixture(scope="module")
def other_user(db):
    """A second user whose notifications must not be visible to test_user."""
    user = User(
        name="Other User",
        username="otheruser",
        password_hash=hash_password("password123"),
        phone_number="9000000001",
        consumer_number="9999999999",
        is_active=True,
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    return user


@pytest.fixture(scope="module")
def client():
    """Return a TestClient bound to the FastAPI app."""
    return TestClient(app)


# ---------------------------------------------------------------------------
# Tests – GET /notifications
# ---------------------------------------------------------------------------

class TestGetNotifications:

    def test_returns_200_with_valid_token(self, client, auth_headers, seed_notifications):
        """Authenticated user receives HTTP 200."""
        response = client.get("/notifications", headers=auth_headers)
        assert response.status_code == 200

    def test_returns_list(self, client, auth_headers, seed_notifications):
        """Response body is a JSON array."""
        response = client.get("/notifications", headers=auth_headers)
        data = response.json()
        assert isinstance(data, list)

    def test_returns_seeded_notifications(self, client, auth_headers, seed_notifications):
        """All seeded notifications are present in the response."""
        response = client.get("/notifications", headers=auth_headers)
        data = response.json()
        titles = [n["title"] for n in data]
        assert "Bill Due" in titles
        assert "High Usage Alert" in titles

    def test_notification_schema(self, client, auth_headers, seed_notifications):
        """Each notification contains the required fields."""
        response = client.get("/notifications", headers=auth_headers)
        data = response.json()
        required_fields = {"id", "title", "message", "type", "priority", "is_read", "created_at"}
        for notif in data:
            assert required_fields.issubset(notif.keys()), (
                f"Missing fields: {required_fields - notif.keys()}"
            )

    def test_returns_401_without_token(self, client):
        """Unauthenticated request is rejected with 401."""
        response = client.get("/notifications")
        assert response.status_code == 401

    def test_returns_401_with_invalid_token(self, client):
        """Request with a bogus token is rejected with 401."""
        response = client.get(
            "/notifications",
            headers={"Authorization": "Bearer this.is.not.valid"}
        )
        assert response.status_code == 401

    def test_only_returns_own_notifications(self, client, db, other_user, seed_notifications):
        """Notifications belonging to another user are not returned."""
        other_notif = Notification(
            user_id=other_user.id,
            title="Other User Notif",
            message="Should not appear for ravikumar.",
            type="general",
            priority=0,
            is_read=False,
        )
        db.add(other_notif)
        db.commit()

        # We can just use the user_id from one of the seeded notifications (which belong to test_user)
        test_user_id = seed_notifications[0].user_id

        # Use ravikumar auth headers directly
        ravi_headers = {"Authorization": f"Bearer {create_access_token(test_user_id, 'ravikumar')}"}
        response = client.get("/notifications", headers=ravi_headers)
        data = response.json()
        titles = [n["title"] for n in data]
        assert "Other User Notif" not in titles

    def test_count_matches_seeded_amount(self, client, auth_headers, seed_notifications):
        """Returned notification count is at least the number we seeded."""
        response = client.get("/notifications", headers=auth_headers)
        data = response.json()
        assert len(data) >= len(seed_notifications)


# ---------------------------------------------------------------------------
# Tests – POST /notifications/read/{id}
# ---------------------------------------------------------------------------

class TestMarkNotificationRead:

    def test_mark_read_returns_200(self, client, auth_headers, seed_notifications):
        """Marking an existing notification as read returns HTTP 200."""
        notif_id = seed_notifications[0].id
        response = client.post(f"/notifications/read/{notif_id}", headers=auth_headers)
        assert response.status_code == 200

    def test_mark_read_response_body(self, client, auth_headers, seed_notifications):
        """Response contains 'message' and correct 'id'."""
        notif_id = seed_notifications[1].id
        response = client.post(f"/notifications/read/{notif_id}", headers=auth_headers)
        data = response.json()
        assert data["message"] == "Marked as read"
        assert data["id"] == notif_id

    def test_notification_is_read_after_marking(self, client, auth_headers, seed_notifications, db):
        """is_read flag is actually set to True in the database."""
        notif_id = seed_notifications[0].id
        client.post(f"/notifications/read/{notif_id}", headers=auth_headers)
        db.expire_all()
        notif = db.query(Notification).filter(Notification.id == notif_id).first()
        assert notif.is_read is True

    def test_mark_read_returns_401_without_token(self, client, seed_notifications):
        """Unauthenticated mark-read request is rejected."""
        notif_id = seed_notifications[0].id
        response = client.post(f"/notifications/read/{notif_id}")
        assert response.status_code == 401

    def test_mark_read_returns_404_for_nonexistent_notification(self, client, auth_headers):
        """Attempting to mark a non-existent notification returns 404."""
        response = client.post("/notifications/read/999999", headers=auth_headers)
        assert response.status_code == 404

    def test_mark_read_returns_404_for_other_users_notification(
        self, client, db, other_user, test_user
    ):
        """User cannot mark another user's notification as read (returns 404)."""
        other_notif = Notification(
            user_id=other_user.id,
            title="Private Notif",
            message="Belongs to other user.",
            type="general",
            priority=0,
            is_read=False,
        )
        db.add(other_notif)
        db.commit()
        db.refresh(other_notif)

        # Log in as ravikumar and try to mark the other user's notification
        ravi_token = create_access_token(test_user.id, test_user.username)
        ravi_headers = {"Authorization": f"Bearer {ravi_token}"}
        response = client.post(
            f"/notifications/read/{other_notif.id}", headers=ravi_headers
        )
        assert response.status_code == 404

    def test_mark_read_idempotent(self, client, auth_headers, seed_notifications):
        """Marking the same notification read twice still returns 200."""
        notif_id = seed_notifications[0].id
        client.post(f"/notifications/read/{notif_id}", headers=auth_headers)
        response = client.post(f"/notifications/read/{notif_id}", headers=auth_headers)
        assert response.status_code == 200

