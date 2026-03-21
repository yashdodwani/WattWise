from sqlalchemy import Column, Integer, String, Float, Boolean, ForeignKey, DateTime, Time, Text
from sqlalchemy.orm import declarative_base, relationship
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.types import TypeDecorator, CHAR
import uuid
from datetime import datetime
from zoneinfo import ZoneInfo

IST = ZoneInfo("Asia/Kolkata")

def now_ist():
    return datetime.now(IST)

class GUID(TypeDecorator):
    """Platform-independent GUID type.

    Uses PostgreSQL's UUID type, otherwise uses
    CHAR(32), storing as stringified hex values.
    """
    impl = CHAR
    cache_ok = True

    def load_dialect_impl(self, dialect):
        if dialect.name == 'postgresql':
            return dialect.type_descriptor(UUID(as_uuid=True))
        else:
            return dialect.type_descriptor(CHAR(32))

    def process_bind_param(self, value, dialect):
        if value is None:
            return value
        elif dialect.name == 'postgresql':
            return str(value)
        else:
            if not isinstance(value, uuid.UUID):
                return "%.32x" % uuid.UUID(value).int
            else:
                # hexstring
                return "%.32x" % value.int

    def process_result_value(self, value, dialect):
        if value is None:
            return value
        else:
            if not isinstance(value, uuid.UUID):
                return uuid.UUID(value)
            else:
                return value

Base = declarative_base()

# ---------------- USERS ----------------
class User(Base):
    __tablename__ = "users"

    id = Column(GUID(), primary_key=True, default=uuid.uuid4, index=True)
    name = Column(String, nullable=False)
    username = Column(String, unique=True, nullable=True, index=True)
    password_hash = Column(String, nullable=True)
    phone_number = Column(String, unique=True, nullable=False, index=True)
    consumer_number = Column(String, unique=True, nullable=False, index=True)
    location = Column(String, nullable=False, default="Surat")
    discom = Column(String, nullable=False, default="DGVCL")
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=now_ist)

    meters = relationship("Meter", back_populates="user")
    appliances = relationship("Appliance", back_populates="user")
    otp_records = relationship("OTPRecord", back_populates="user")
    transactions = relationship("Transaction", back_populates="user")


# ---------------- METERS ----------------
class Meter(Base):
    __tablename__ = "meters"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(GUID(), ForeignKey("users.id"))

    user = relationship("User", back_populates="meters")
    readings = relationship("MeterReading", back_populates="meter")


# ---------------- METER READINGS ----------------
class MeterReading(Base):
    __tablename__ = "meter_readings"

    id = Column(Integer, primary_key=True, index=True)
    meter_id = Column(Integer, ForeignKey("meters.id"))
    timestamp = Column(DateTime, default=now_ist)
    energy_kwh = Column(Float)

    meter = relationship("Meter", back_populates="readings")


# ---------------- APPLIANCES ----------------
class Appliance(Base):
    __tablename__ = "appliances"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(GUID(), ForeignKey("users.id"))

    name = Column(String)
    power_kw = Column(Float)

    is_on = Column(Boolean, default=False)
    last_started_at = Column(DateTime, nullable=True)

    user = relationship("User", back_populates="appliances")


# ---------------- TARIFFS ----------------
class Tariff(Base):
    __tablename__ = "tariffs"

    id = Column(Integer, primary_key=True, index=True)
    start_time = Column(Time)
    end_time = Column(Time)
    price_per_unit = Column(Float)


# ---------------- SCHEDULES ----------------
class Schedule(Base):
    __tablename__ = "schedules"

    id = Column(Integer, primary_key=True, index=True)
    appliance_id = Column(Integer, ForeignKey("appliances.id"))
    start_time = Column(DateTime)
    end_time = Column(DateTime)

class ApplianceUsage(Base):
    __tablename__ = "appliance_usage"

    id = Column(Integer, primary_key=True, index=True)
    appliance_id = Column(Integer, ForeignKey("appliances.id"))

    start_time = Column(DateTime)
    end_time = Column(DateTime)
    energy_kwh = Column(Float)


# ---------------- OTP RECORDS ----------------
class OTPRecord(Base):
    __tablename__ = "otp_records"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(GUID(), ForeignKey("users.id"))
    otp_code = Column(String)
    created_at = Column(DateTime, default=now_ist)
    expires_at = Column(DateTime)
    is_used = Column(Boolean, default=False)

    user = relationship("User", back_populates="otp_records")


# ---------------- BILLS ----------------
class Bill(Base):
    __tablename__ = "bills"

    id = Column(Integer, primary_key=True)
    user_id = Column(GUID(), ForeignKey("users.id"))
    units = Column(Float)
    amount = Column(Float)
    status = Column(String, default="unpaid")
    due_date = Column(DateTime)
    created_at = Column(DateTime, default=now_ist)


# ---------------- COMPLAINTS ----------------
class Complaint(Base):
    __tablename__ = "complaints"

    id = Column(Integer, primary_key=True)
    user_id = Column(GUID(), ForeignKey("users.id"))
    type = Column(String)
    description = Column(String)
    status = Column(String, default="OPEN")
    created_at = Column(DateTime, default=now_ist)
    resolved_at = Column(DateTime, nullable=True)


# ---------------- OUTAGES ----------------
class Outage(Base):
    __tablename__ = "outages"

    id = Column(Integer, primary_key=True)
    area = Column(String)
    reason = Column(String)
    status = Column(String, default="ACTIVE")
    start_time = Column(DateTime)
    expected_restore = Column(DateTime)
    created_at = Column(DateTime, default=now_ist)


# ---------------- NOTIFICATIONS ----------------
class Notification(Base):
    __tablename__ = "notifications"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(GUID(), ForeignKey("users.id"), index=True)
    title = Column(String, nullable=False)
    message = Column(Text, nullable=False)
    type = Column(String, nullable=False, default="general")  # bill / appliance / recommendation / warning
    priority = Column(Integer, default=0)
    is_read = Column(Boolean, default=False)
    created_at = Column(DateTime, default=now_ist)


# ---------------- TRANSACTIONS (REVENUE) ----------------
class Transaction(Base):
    __tablename__ = "transactions"

    transaction_id = Column(Integer, primary_key=True, index=True)
    user_id = Column(GUID(), ForeignKey("users.id"))
    amount = Column(Float, nullable=False)
    payment_method = Column(String, nullable=False)  # UPI, Net Banking, Credit Card, Wallet
    status = Column(String, default="SUCCESS")  # SUCCESS, PENDING, FAILED
    created_at = Column(DateTime, default=now_ist)

    user = relationship("User", back_populates="transactions")


# ---------------- SMS LOGS & TEMPLATES ----------------
class SMSLog(Base):
    __tablename__ = "sms_logs"

    sms_id = Column(Integer, primary_key=True, index=True)
    user_id = Column(GUID(), ForeignKey("users.id"), nullable=True)  # Can be null if sent to unknown number? Assume linked to user.
    phone_number = Column(String, nullable=False)
    message = Column(Text, nullable=False)
    status = Column(String, default="SENT")  # SENT, DELIVERED, FAILED
    sent_at = Column(DateTime, default=now_ist)

class SMSTemplate(Base):
    __tablename__ = "sms_templates"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, unique=True, nullable=False)  # e.g., "bill_due_reminder"
    message_body = Column(Text, nullable=False)
    created_at = Column(DateTime, default=now_ist)

