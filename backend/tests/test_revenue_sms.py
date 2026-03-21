import sys
import os
from datetime import datetime

# Make sure the backend package is importable when running from the tests/ dir
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from db.models import Base, User, Transaction, SMSLog, SMSTemplate
from db.models import GUID
from db.session import get_db
from utils.security import hash_password, create_access_token
from main import app
import uuid

# ---------------------------------------------------------------------------
# In-memory SQLite test database
# ---------------------------------------------------------------------------
TEST_DATABASE_URL = "sqlite:///./test_revenue_sms.db"

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

app.dependency_overrides[get_db] = override_get_db

# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture(scope="module", autouse=True)
def setup_db():
    Base.metadata.create_all(bind=engine)
    yield
    Base.metadata.drop_all(bind=engine)
    engine.dispose()
    db_file = os.path.join(os.path.dirname(__file__), "..", "test_revenue_sms.db")
    try:
        if os.path.exists(db_file):
            os.remove(db_file)
    except PermissionError:
        pass

@pytest.fixture(scope="module")
def db():
    session = TestingSessionLocal()
    yield session
    session.close()

@pytest.fixture(scope="module")
def test_user(db):
    user = User(
        name="Test User",
        username="testuser",
        password_hash=hash_password("password"),
        phone_number="1234567890",
        consumer_number="1111111111",
        is_active=True,
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    return user

@pytest.fixture(scope="module")
def client():
    return TestClient(app)

@pytest.fixture(scope="module")
def seed_transactions(db, test_user):
    t1 = Transaction(
        user_id=test_user.id,
        amount=150.0,
        payment_method="UPI",
        status="SUCCESS",
        created_at=datetime.now()
    )
    t2 = Transaction(
        user_id=test_user.id,
        amount=600.0,
        payment_method="Credit Card",
        status="PENDING",
        created_at=datetime.now()
    )
    db.add_all([t1, t2])
    db.commit()
    return [t1, t2]

@pytest.fixture(scope="module")
def seed_templates(db):
    t1 = SMSTemplate(name="welcome", message_body="Welcome to WattWise!")
    db.add(t1)
    db.commit()
    db.refresh(t1)
    return t1

# ---------------------------------------------------------------------------
# Revenue Tests
# ---------------------------------------------------------------------------

def test_get_transactions(client, seed_transactions):
    response = client.get("/api/revenue/transactions")
    assert response.status_code == 200
    data = response.json()
    assert len(data) >= 2
    assert data[0]["amount"] == 150.0

def test_revenue_summary(client, seed_transactions):
    response = client.get("/api/revenue/summary")
    assert response.status_code == 200
    data = response.json()
    # 150 (success) + 600 (pending) = 750 total in DB logic?
    # Current implementation sums all amount for total_revenue?
    # Let's check implementation: total_revenue = db.query(func.sum(Transaction.amount)).scalar()
    # Yes, it sums all.
    assert data["total_revenue"] == 750.0
    assert data["pending_revenue"] == 600.0
    assert data["highest_payment"] == 600.0

def test_revenue_payment_methods(client, seed_transactions):
    response = client.get("/api/revenue/payment-methods")
    assert response.status_code == 200
    data = response.json()
    assert data["UPI"] >= 1
    assert data["Credit Card"] >= 1

def test_recharge_distribution(client, seed_transactions):
    response = client.get("/api/revenue/recharge-distribution")
    assert response.status_code == 200
    data = response.json()
    # 150 is in 100-500
    # 600 is in 500-1000
    assert data["100-500"] >= 1
    assert data["500-1000"] >= 1

# ---------------------------------------------------------------------------
# SMS Tests
# ---------------------------------------------------------------------------

def test_send_sms(client, test_user):
    payload = {
        "user_id": str(test_user.id),
        "phone_number": "9876543210",
        "message": "Test SMS"
    }
    response = client.post("/api/sms/send", json=payload)
    assert response.status_code == 200
    data = response.json()
    assert data["phone_number"] == "9876543210"
    assert data["message"] == "Test SMS"
    assert "sms_id" in data

def test_get_sms_templates(client, seed_templates):
    response = client.get("/api/sms/templates")
    assert response.status_code == 200
    data = response.json()
    assert len(data) >= 1
    assert data[0]["name"] == "welcome"

def test_update_sms_template(client, seed_templates):
    t_id = seed_templates.id
    payload = {
        "name": "welcome_updated",
        "message_body": "Updated Welcome Message"
    }
    response = client.put(f"/api/sms/templates/{t_id}", json=payload)
    assert response.status_code == 200
    data = response.json()
    assert data["name"] == "welcome_updated"
    assert data["message_body"] == "Updated Welcome Message"
