import os
import sys
import pytest
from typing import Dict, Generator
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, Engine
from sqlalchemy.orm import sessionmaker, Session

# Add project root to Python path
project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, project_root)

from app.database.models import Base, User, Penalty, get_engine
from app.config.settings import get_settings, Settings
from main import app
from app.database.crud import get_db

def get_test_settings() -> Settings:
    """Get test settings with in-memory SQLite database"""
    return Settings(
        DATABASE_URL="sqlite:///:memory:",
        PORT=8011,
        PROJECT_NAME="Balance Up API Test",
        DEBUG=False,
        RATE_LIMIT_MAX_REQUESTS=50,
        RATE_LIMIT_WINDOW=60
    )

@pytest.fixture(scope="session")
def settings() -> Settings:
    """Test settings fixture"""
    return get_test_settings()

def get_test_engine() -> Engine:
    """Get or create test database engine"""
    settings = get_test_settings()
    engine = create_engine(
        settings.DATABASE_URL,
        connect_args={"check_same_thread": False}
    )
    # Create all tables in the test database
    Base.metadata.create_all(bind=engine)
    return engine

@pytest.fixture(scope="function")
def db_engine():
    """Create a test database engine and clean up after each test"""
    engine = get_test_engine()
    Base.metadata.drop_all(bind=engine)
    Base.metadata.create_all(bind=engine)
    return engine

@pytest.fixture(scope="function")
def db_session(db_engine) -> Generator[Session, None, None]:
    """Get a test database session"""
    TestingSessionLocal = sessionmaker(
        autocommit=False,
        autoflush=False,
        bind=db_engine
    )
    
    session = TestingSessionLocal()
    try:
        yield session
    finally:
        session.close()

@pytest.fixture(scope="function")
def client(settings, db_engine) -> TestClient:
    """Test client fixture with database and settings overrides"""
    # Override get_engine to return our test engine
    app.dependency_overrides[get_engine] = lambda: db_engine
    
    def override_get_settings():
        return settings
    
    app.dependency_overrides[get_settings] = override_get_settings
    
    # Create a test client using the overridden dependencies
    with TestClient(app) as test_client:
        yield test_client
    
    app.dependency_overrides.clear()

@pytest.fixture
def test_user() -> Dict:
    """Sample test user data"""
    return {
        "username": "testuser",
        "email": "test@example.com"
    }

@pytest.fixture
def test_penalty() -> Dict:
    """Sample test penalty data"""
    return {
        "user_id": 1,
        "amount": 50.0,
        "reason": "Test Penalty",
        "paid": False
    }