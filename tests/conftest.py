"""Pytest fixtures for testing."""

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.main import app
from app.database import Base, get_db


# Use in-memory SQLite for testing with StaticPool to share connection
# StaticPool is required for in-memory SQLite to persist tables across connections
SQLALCHEMY_TEST_DATABASE_URL = "sqlite:///:memory:"

engine = create_engine(
    SQLALCHEMY_TEST_DATABASE_URL,
    connect_args={"check_same_thread": False},
    poolclass=StaticPool,  # Required for in-memory SQLite
)
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


@pytest.fixture(scope="function")
def db_session():
    """Create a fresh database for each test."""
    Base.metadata.create_all(bind=engine)
    db = TestingSessionLocal()
    try:
        yield db
    finally:
        db.close()
        Base.metadata.drop_all(bind=engine)


@pytest.fixture(scope="function")
def client(db_session):
    """Create a test client with test database."""
    def override_get_db():
        try:
            yield db_session
        finally:
            pass
    
    app.dependency_overrides[get_db] = override_get_db
    yield TestClient(app)
    app.dependency_overrides.clear()


@pytest.fixture
def sample_complaint():
    """Sample customer complaint for testing."""
    return "I was charged twice for order #12345. This is unacceptable!"


@pytest.fixture
def mock_ai_response():
    """Mock AI response for testing."""
    from models.schemas import AITriageResponse
    from models.enums import TicketCategory, UrgencyLevel
    return AITriageResponse(
        category=TicketCategory.BILLING,
        sentiment_score=3,
        urgency=UrgencyLevel.HIGH,
        draft_response="We sincerely apologize for the double charge. We're investigating this immediately."
    )
