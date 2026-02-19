from sqlalchemy import Column, Integer, String, Float, Boolean, ForeignKey, DateTime, Time
from sqlalchemy.orm import declarative_base, relationship
from datetime import datetime
from zoneinfo import ZoneInfo

IST = ZoneInfo("Asia/Kolkata")

def now_ist():
    return datetime.now(IST)

Base = declarative_base()

# ---------------- USERS ----------------
class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, nullable=False)

    meters = relationship("Meter", back_populates="user")
    appliances = relationship("Appliance", back_populates="user")


# ---------------- METERS ----------------
class Meter(Base):
    __tablename__ = "meters"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"))

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
    user_id = Column(Integer, ForeignKey("users.id"))

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