"""
SQLAlchemy ORM models for users, appliances, and tariffs (placeholders).
Define minimal models for development and migration scripts.
"""
from sqlalchemy import Column, Integer, String, Float, DateTime, Boolean, ForeignKey
from sqlalchemy.ext.declarative import declarative_base
import datetime

Base = declarative_base()


class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    email = Column(String, unique=True, index=True, nullable=False)
    name = Column(String, nullable=True)


class Appliance(Base):
    __tablename__ = "appliances"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    name = Column(String, nullable=False)
    power_watts = Column(Float, nullable=False, default=0.0)
    is_on = Column(Boolean, default=False)


class Tariff(Base):
    __tablename__ = "tariffs"

    id = Column(Integer, primary_key=True, index=True)
    start = Column(DateTime, nullable=False, default=datetime.datetime.utcnow)
    end = Column(DateTime, nullable=False, default=datetime.datetime.utcnow)
    price_per_kwh = Column(Float, nullable=False, default=0.0)

