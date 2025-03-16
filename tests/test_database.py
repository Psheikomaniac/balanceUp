import os
import pytest
import tempfile
from datetime import datetime
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.database.models import Base, User, Penalty, Transaction, AuditLog
from app.database.migrate_db import migrate_db
from app.database import crud
from app.database import schemas

@pytest.fixture
def temp_db():
    """Create a temporary database for testing"""
    db_fd, db_path = tempfile.mkstemp()
    db_url = f"sqlite:///{db_path}"
    engine = create_engine(db_url, connect_args={"check_same_thread": False})
    TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    
    # Create tables
    Base.metadata.create_all(bind=engine)
    
    # Create a test session
    session = TestingSessionLocal()
    
    yield session
    
    # Cleanup
    session.close()
    os.close(db_fd)
    os.unlink(db_path)

def test_create_user(temp_db):
    """Test user creation"""
    user_data = schemas.UserCreate(
        name="Test User",
        email="test@example.com",
        phone="1234567890"
    )
    
    user = crud.create_user(temp_db, user_data)
    assert user is not None
    assert user.name == "Test User"
    assert user.email == "test@example.com"
    assert user.phone == "1234567890"
    assert user.id is not None  # Should be a UUID string

def test_create_penalty(temp_db):
    """Test penalty creation"""
    # Create a user first
    user_data = schemas.UserCreate(name="Test User", email="test@example.com")
    user = crud.create_user(temp_db, user_data)
    
    # Create a penalty
    penalty_data = schemas.PenaltyCreate(
        user_id=user.id,
        amount=100.0,
        reason="Test penalty"
    )
    
    penalty = crud.create_penalty(temp_db, penalty_data)
    assert penalty is not None
    assert penalty.amount == 100.0
    assert penalty.reason == "Test penalty"
    assert penalty.user_id == user.id
    assert not penalty.paid

def test_mark_penalty_paid(temp_db):
    """Test marking a penalty as paid"""
    # Create user and penalty
    user = crud.create_user(temp_db, schemas.UserCreate(name="Test User"))
    penalty = crud.create_penalty(
        temp_db,
        schemas.PenaltyCreate(user_id=user.id, amount=100.0)
    )
    
    # Mark as paid
    updated_penalty = crud.mark_penalty_paid(temp_db, penalty.penalty_id)
    assert updated_penalty.paid
    assert updated_penalty.paid_at is not None

def test_create_transaction(temp_db):
    """Test transaction creation"""
    # Create user
    user = crud.create_user(temp_db, schemas.UserCreate(name="Test User"))
    
    # Create transaction
    transaction_data = schemas.TransactionCreate(
        user_id=user.id,
        amount=50.0,
        description="Test payment"
    )
    
    transaction = crud.create_transaction(temp_db, transaction_data)
    assert transaction is not None
    assert transaction.amount == 50.0
    assert transaction.user_id == user.id

def test_user_total_penalties(temp_db):
    """Test user's total penalties calculation"""
    # Create user
    user = crud.create_user(temp_db, schemas.UserCreate(name="Test User"))
    
    # Create multiple penalties
    penalties = [
        schemas.PenaltyCreate(user_id=user.id, amount=100.0),
        schemas.PenaltyCreate(user_id=user.id, amount=50.0),
        schemas.PenaltyCreate(user_id=user.id, amount=75.0)
    ]
    
    for penalty_data in penalties:
        crud.create_penalty(temp_db, penalty_data)
    
    # Get user with penalties
    db_user = crud.get_user(temp_db, user.id)
    assert db_user.total_unpaid_penalties == 225.0  # 100 + 50 + 75

def test_cascade_delete(temp_db):
    """Test that deleting a user cascades to related penalties"""
    # Create user with penalties
    user = crud.create_user(temp_db, schemas.UserCreate(name="Test User"))
    crud.create_penalty(temp_db, schemas.PenaltyCreate(user_id=user.id, amount=100.0))
    crud.create_penalty(temp_db, schemas.PenaltyCreate(user_id=user.id, amount=50.0))
    
    # Delete user
    crud.delete_user(temp_db, user.id)
    
    # Check that penalties were deleted
    penalties = crud.get_user_penalties(temp_db, user.id)
    assert len(penalties) == 0

def test_user_search(temp_db):
    """Test user search functionality"""
    # Create test users
    users_data = [
        schemas.UserCreate(name="John Doe", email="john@example.com"),
        schemas.UserCreate(name="Jane Smith", email="jane@example.com"),
        schemas.UserCreate(name="John Smith", email="john.smith@example.com")
    ]
    
    for user_data in users_data:
        crud.create_user(temp_db, user_data)
    
    # Search by name
    results = crud.get_users(temp_db, search="John")
    assert len(results) == 2
    
    # Search by email
    results = crud.get_users(temp_db, search="jane@")
    assert len(results) == 1
    assert results[0].name == "Jane Smith"

def test_audit_logging(temp_db):
    """Test audit logging functionality"""
    # Create a test user
    user = crud.create_user(temp_db, schemas.UserCreate(name="Test User"))
    
    # Create an audit log entry
    log_entry = schemas.AuditLogCreate(
        action="CREATE",
        entity_type="USER",
        entity_id=user.id,
        user_id=user.id,
        details="Created new user account"
    )
    
    audit_log = crud.create_audit_log(temp_db, log_entry)
    assert audit_log is not None
    assert audit_log.action == "CREATE"
    assert audit_log.entity_type == "USER"
    assert audit_log.entity_id == user.id