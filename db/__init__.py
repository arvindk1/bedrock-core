"""Database session management."""

import os
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from db.models import Base

DATABASE_URL = os.environ.get("DATABASE_URL", "sqlite:///./trading.db")

engine = create_engine(
    DATABASE_URL,
    connect_args={"check_same_thread": False}
    if DATABASE_URL.startswith("sqlite")
    else {},
)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


def init_db():
    """Create all tables if they don't exist."""
    Base.metadata.create_all(bind=engine)


def get_db():
    """FastAPI dependency: yields a DB session and ensures it's closed."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
