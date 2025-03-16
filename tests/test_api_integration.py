import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
import tempfile
import os

from app.main import app
from app.database.models import Base
from app.database import get_db
from app.config.settings import get_settings

settings = get_settings()

@pytest.fixture(scope="module")
def test_client():
    """Create a test client for the API"""
    # Create a temporary database
    db_fd, db_path = tempfile.mkstemp()
    db_url = f"sqlite:///{db_path}"
    
    # Override the database URL
    settings.DATABASE_URL = db_url
    
    # Create test database
    engine = create_engine(db_url, connect_args={"check_same_thread": False})
    TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    Base.metadata.create_all(bind=engine)
    
    # Override the get_db dependency
    def override_get_db():
        try:
            db = TestingSessionLocal()
            yield db
        finally:
            db.close()
    
    app.dependency_overrides[get_db] = override_get_db
    
    # Create test client
    with TestClient(app) as client:
        yield client
    
    # Cleanup
    os.close(db_fd)
    os.unlink(db_path)

@pytest.fixture
def user_data():
    """Sample user data for testing"""
    return {
        "name": "Test User",
        "email": "test@example.com",
        "phone": "1234567890"
    }

@pytest.fixture
def penalty_data():
    """Sample penalty data for testing"""
    return {
        "amount": 100.0,
        "reason": "Test Penalty"
    }

def test_create_user(test_client, user_data):
    """Test user creation endpoint"""
    response = test_client.post("/api/v1/users/", json=user_data)
    assert response.status_code == 201
    data = response.json()
    assert data["name"] == user_data["name"]
    assert data["email"] == user_data["email"]
    assert "id" in data
    return data

def test_get_user(test_client, user_data):
    """Test get user endpoint"""
    # Create user first
    user = test_create_user(test_client, user_data)
    
    # Get user
    response = test_client.get(f"/api/v1/users/{user['id']}")
    assert response.status_code == 200
    data = response.json()
    assert data["name"] == user_data["name"]
    assert data["email"] == user_data["email"]

def test_create_penalty(test_client, user_data, penalty_data):
    """Test penalty creation endpoint"""
    # Create user first
    user = test_create_user(test_client, user_data)
    
    # Create penalty
    penalty_data["user_id"] = user["id"]
    response = test_client.post("/api/v1/penalties/", json=penalty_data)
    assert response.status_code == 201
    data = response.json()
    assert data["amount"] == penalty_data["amount"]
    assert data["reason"] == penalty_data["reason"]
    assert data["user_id"] == user["id"]
    assert not data["paid"]
    return data

def test_mark_penalty_paid(test_client, user_data, penalty_data):
    """Test marking a penalty as paid"""
    # Create user and penalty first
    penalty = test_create_penalty(test_client, user_data, penalty_data)
    
    # Mark penalty as paid
    response = test_client.post(f"/api/v1/penalties/{penalty['penalty_id']}/mark-paid")
    assert response.status_code == 200
    data = response.json()
    assert data["paid"]
    assert data["paid_at"] is not None

def test_get_user_penalties(test_client, user_data, penalty_data):
    """Test getting penalties for a user"""
    # Create user and penalties
    user = test_create_user(test_client, user_data)
    
    # Create multiple penalties
    penalty_data["user_id"] = user["id"]
    test_client.post("/api/v1/penalties/", json=penalty_data)
    test_client.post("/api/v1/penalties/", json=penalty_data)
    
    # Get user's penalties
    response = test_client.get(f"/api/v1/users/{user['id']}/penalties")
    assert response.status_code == 200
    data = response.json()
    assert len(data) == 2
    assert all(p["user_id"] == user["id"] for p in data)

def test_get_user_balance(test_client, user_data, penalty_data):
    """Test getting user's balance"""
    # Create user and penalties
    user = test_create_user(test_client, user_data)
    
    # Create multiple penalties with different amounts
    penalties = [
        {"user_id": user["id"], "amount": 100.0, "reason": "Penalty 1"},
        {"user_id": user["id"], "amount": 50.0, "reason": "Penalty 2"}
    ]
    
    for penalty in penalties:
        test_client.post("/api/v1/penalties/", json=penalty)
    
    # Get user's balance
    response = test_client.get(f"/api/v1/users/{user['id']}/balance")
    assert response.status_code == 200
    balance = response.json()
    assert balance == 150.0  # Sum of unpaid penalties

def test_create_transaction(test_client, user_data):
    """Test transaction creation endpoint"""
    # Create user first
    user = test_create_user(test_client, user_data)
    
    # Create transaction
    transaction_data = {
        "user_id": user["id"],
        "amount": 75.0,
        "description": "Test payment"
    }
    
    response = test_client.post("/api/v1/transactions/", json=transaction_data)
    assert response.status_code == 201
    data = response.json()
    assert data["amount"] == transaction_data["amount"]
    assert data["user_id"] == user["id"]
    assert data["description"] == transaction_data["description"]

def test_pay_penalty(test_client, user_data, penalty_data):
    """Test paying a penalty through transaction"""
    # Create user and penalty
    penalty = test_create_penalty(test_client, user_data, penalty_data)
    
    # Pay the penalty
    response = test_client.post(f"/api/v1/transactions/pay-penalty/{penalty['penalty_id']}")
    assert response.status_code == 200
    data = response.json()
    assert data["amount"] == penalty_data["amount"]
    
    # Verify penalty is marked as paid
    response = test_client.get(f"/api/v1/penalties/{penalty['penalty_id']}")
    assert response.status_code == 200
    penalty_data = response.json()
    assert penalty_data["paid"]

def test_get_penalties_summary(test_client, user_data, penalty_data):
    """Test getting penalties summary statistics"""
    # Create user and penalties
    user = test_create_user(test_client, user_data)
    penalty_data["user_id"] = user["id"]
    
    # Create penalties with different amounts
    penalties = [
        {"user_id": user["id"], "amount": 100.0, "reason": "Penalty 1"},
        {"user_id": user["id"], "amount": 50.0, "reason": "Penalty 2"},
        {"user_id": user["id"], "amount": 75.0, "reason": "Penalty 3"}
    ]
    
    for penalty in penalties:
        test_client.post("/api/v1/penalties/", json=penalty)
    
    # Mark one penalty as paid
    first_penalty_response = test_client.post("/api/v1/penalties/", json=penalties[0])
    first_penalty = first_penalty_response.json()
    test_client.post(f"/api/v1/penalties/{first_penalty['penalty_id']}/mark-paid")
    
    # Get summary
    response = test_client.get("/api/v1/penalties/statistics/summary")
    assert response.status_code == 200
    data = response.json()
    
    assert data["total_count"] == 4  # 3 penalties + 1 marked as paid
    assert data["paid_count"] == 1
    assert data["unpaid_count"] == 3
    assert data["total_amount"] == 325.0  # 100 + 50 + 75 + 100
    assert data["paid_amount"] == 100.0
    assert data["unpaid_amount"] == 225.0  # 50 + 75 + 100