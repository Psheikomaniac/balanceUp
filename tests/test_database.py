import os
import pytest
import tempfile
from datetime import datetime
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.exc import IntegrityError

from app.database.models import Base, User, Penalty, Transaction, AuditLog
from app.database.migrate_db import migrate_db
from app.database import crud
from app.database import schemas
from app.errors.exceptions import ResourceNotFoundException

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

def test_create_user(db_session):
    """Test user creation with validation"""
    user = User(
        name="Test User",
        email="test@example.com",
        phone="+1234567890"
    )
    db_session.add(user)
    db_session.commit()
    
    assert user.id is not None
    assert user.created_at is not None
    assert user.updated_at is not None

def test_create_penalty(db_session, test_user):
    """Test penalty creation and relationships"""
    penalty = Penalty(
        user_id=test_user.id,
        amount=100.0,
        reason="Test penalty"
    )
    db_session.add(penalty)
    db_session.commit()
    
    assert penalty.penalty_id is not None
    assert penalty.user_id == test_user.id
    assert penalty.paid is False
    assert penalty.paid_at is None

def test_mark_penalty_paid(db_session, test_penalty):
    """Test marking a penalty as paid"""
    test_penalty.mark_as_paid()
    db_session.commit()
    
    assert test_penalty.paid is True
    assert test_penalty.paid_at is not None

def test_create_transaction(db_session, test_user):
    """Test transaction creation and relationships"""
    transaction = Transaction(
        user_id=test_user.id,
        amount=50.0,
        description="Test transaction"
    )
    db_session.add(transaction)
    db_session.commit()
    
    assert transaction.transaction_id is not None
    assert transaction.user_id == test_user.id
    assert transaction.created_at is not None

def test_cascade_delete(db_session, test_user, test_penalty):
    """Test that deleting a user cascades to related penalties"""
    db_session.delete(test_user)
    db_session.commit()
    
    # Check that penalty was deleted
    penalty = db_session.query(Penalty).filter_by(penalty_id=test_penalty.penalty_id).first()
    assert penalty is None

def test_user_penalties_calculation(db_session, test_user):
    """Test user's penalty calculations"""
    # Create some penalties
    penalties = [
        Penalty(user_id=test_user.id, amount=100.0),
        Penalty(user_id=test_user.id, amount=200.0),
        Penalty(user_id=test_user.id, amount=300.0, paid=True)
    ]
    db_session.add_all(penalties)
    db_session.commit()
    
    assert test_user.total_unpaid_penalties == 300.0
    assert test_user.total_paid_penalties == 300.0

def test_audit_logging(db_session, test_user):
    """Test audit logging functionality"""
    audit_log = AuditLog(
        action="test_action",
        entity_type="user",
        entity_id=test_user.id,
        user_id=test_user.id,
        details="Test audit log entry"
    )
    db_session.add(audit_log)
    db_session.commit()
    
    assert audit_log.log_id is not None
    assert audit_log.timestamp is not None
    assert audit_log.user_id == test_user.id

def test_user_unique_email(db_session):
    """Test that users cannot have duplicate emails"""
    user1 = User(name="User 1", email="same@example.com")
    user2 = User(name="User 2", email="same@example.com")
    
    db_session.add(user1)
    db_session.commit()
    
    with pytest.raises(IntegrityError):
        db_session.add(user2)
        db_session.commit()

def test_penalties_summary(db_session, test_user):
    """Test penalties summary calculation"""
    # Create a mix of paid and unpaid penalties
    penalties = [
        Penalty(user_id=test_user.id, amount=100.0),
        Penalty(user_id=test_user.id, amount=200.0, paid=True),
        Penalty(user_id=test_user.id, amount=300.0)
    ]
    db_session.add_all(penalties)
    db_session.commit()
    
    summary = crud.get_penalties_summary(db_session)
    
    assert summary["total_count"] == 3
    assert summary["paid_count"] == 1
    assert summary["unpaid_count"] == 2
    assert summary["total_amount"] == 600.0
    assert summary["paid_amount"] == 200.0
    assert summary["unpaid_amount"] == 400.0

def test_transaction_creation_marks_penalty_paid(db_session, test_penalty):
    """Test that creating a transaction properly marks the penalty as paid"""
    transaction = Transaction(
        user_id=test_penalty.user_id,
        amount=test_penalty.amount,
        description=f"Payment for penalty {test_penalty.penalty_id}"
    )
    db_session.add(transaction)
    
    test_penalty.mark_as_paid()
    db_session.commit()
    
    assert test_penalty.paid is True
    assert test_penalty.paid_at is not None
    assert transaction.transaction_id is not None

def test_user_not_found(db_session):
    """Test handling of non-existent user"""
    with pytest.raises(ResourceNotFoundException):
        crud.get_user(db_session, "nonexistent-id")