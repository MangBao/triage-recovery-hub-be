"""Database connection and session management."""

from sqlalchemy import create_engine
from sqlalchemy.orm import declarative_base, sessionmaker
from app.config import settings

# Create database engine with connection pooling
engine = create_engine(
    settings.DATABASE_URL,
    echo=settings.DEBUG,  # SQL logging in debug mode
    pool_size=20,         # Increased from 10 for better concurrency
    max_overflow=30,      # Increased from 20 for burst handling
    pool_pre_ping=True,   # Test connection health before using
    pool_timeout=30,      # Wait up to 30s for available connection
)

# Session factory
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# Base class for ORM models
Base = declarative_base()


def get_db():
    """
    Dependency function for FastAPI endpoints.
    Provides database session with automatic cleanup.
    """
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
