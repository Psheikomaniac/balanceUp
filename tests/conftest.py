import os
import sys
import pytest
import tempfile
from typing import Generator
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, Session

# Add project root to Python path
project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, project_root)

from app.database import Base, get_db
from app.database.models import User, Penalty, Transaction, AuditLog
from app.config.settings import get_settings
from app.database.migrate_db import migrate_db

def get_test_db_url() -> str:
    """Get test database URL"""
    return "sqlite:///:memory:"

@pytest.fixture(scope="session")
def engine():
    """Create database engine for testing"""
    return create_engine(
        get_test_db_url(),
        connect_args={"check_same_thread": False}
    )

@pytest.fixture(scope="function")
def db_session(engine) -> Generator[Session, None, None]:
    """Create a new database session for a test"""
    # Create all tables
    Base.metadata.drop_all(bind=engine)
    Base.metadata.create_all(bind=engine)
    
    # Create session
    TestingSessionLocal = sessionmaker(bind=engine)
    session = TestingSessionLocal()
    
    try:
        yield session
    finally:
        session.close()
        Base.metadata.drop_all(bind=engine)

@pytest.fixture
def test_user(db_session) -> User:
    """Create a test user"""
    user = User(
        name="Test User",
        email="test@example.com"
    )
    db_session.add(user)
    db_session.commit()
    db_session.refresh(user)
    return user

@pytest.fixture
def test_penalty(db_session, test_user) -> Penalty:
    """Create a test penalty"""
    penalty = Penalty(
        user_id=test_user.id,
        amount=100.0,
        reason="Test Penalty"
    )
    db_session.add(penalty)
    db_session.commit()
    db_session.refresh(penalty)
    return penalty

@pytest.fixture
def test_transaction(db_session, test_user) -> Transaction:
    """Create a test transaction"""
    transaction = Transaction(
        user_id=test_user.id,
        amount=50.0,
        description="Test Transaction"
    )
    db_session.add(transaction)
    db_session.commit()
    db_session.refresh(transaction)
    return transaction

@pytest.fixture
def client(engine) -> TestClient:
    """Create test client"""
    from main import app
    
    def override_get_db():
        TestingSessionLocal = sessionmaker(bind=engine)
        db = TestingSessionLocal()
        try:
            yield db
        finally:
            db.close()
    
    # Override the get_db dependency
    app.dependency_overrides[get_db] = override_get_db
    
    with TestClient(app) as test_client:
        yield test_client
        
    app.dependency_overrides.clear()