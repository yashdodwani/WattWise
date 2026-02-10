"""
Seed script to populate the database with dummy users, appliances, and tariffs.
This is a placeholder and does not execute automatically.
"""
from .models import User, Appliance, Tariff, Base
from .session import engine


def create_schema():
    """Create tables in the database (placeholder)."""
    Base.metadata.create_all(bind=engine)


def seed_dummy_data():
    """Insert dummy data into the database (placeholder)."""
    # Implement seeding logic using SessionLocal from session.py when ready.
    pass

