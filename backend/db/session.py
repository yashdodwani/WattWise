"""
SQLAlchemy session setup for PostgreSQL.
Loads DATABASE_URL from environment (via python-dotenv) instead of hardcoding.
NOTE: create a `.env` file with DATABASE_URL or export the env var before running.
"""
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
import os
import warnings

from dotenv import load_dotenv

# Load environment variables from a .env file if present
load_dotenv()

# Read database URL from environment
DATABASE_URL = os.getenv("DATABASE_URL")
if not DATABASE_URL:
    warnings.warn(
        "DATABASE_URL environment variable not set. Using placeholder fallback; update your .env or environment for production.",
        UserWarning,
    )
    # Fallback placeholder (for local development only). Replace with a real URL in production.
    DATABASE_URL = "postgresql+psycopg2://user:password@localhost:5432/wattwise_db"

engine = create_engine(DATABASE_URL, echo=False)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


def get_db():
    """Yield a database session (use with dependency injection in FastAPI)."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
