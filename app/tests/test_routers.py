import pytest
from fastapi.testclient import TestClient
from sqlmodel import Session, SQLModel, create_engine
from app.main import app
from app.database import get_db

# Test database setup
TEST_DATABASE_URL = "sqlite:///test_database.db"
engine = create_engine(TEST_DATABASE_URL)
SQLModel.metadata.create_all(engine)

@pytest.fixture(name="session")
def session_fixture():
    with Session(engine) as session:
        yield session

@pytest.fixture(name="client")
def client_fixture(session: Session):
    def get_db_override():
        return session
    
    app.dependency_overrides[get_db] = get_db_override
    client = TestClient(app)
    yield client
    app.dependency_overrides.clear()

def test_create_and_read_team(client: TestClient):
    # Test team creation
    response = client.post("/teams/", json={"name": "Test Team"})
    assert response.status_code == 200
    data = response.json()
    assert data["name"] == "Test Team"
    
    # Test team listing
    response = client.get("/teams/")
    assert response.status_code == 200
    assert len(response.json()) == 1

def test_csv_import(client: TestClient, session: Session):
    # First create a team
    client.post("/teams/", json={"name": "HSG WBW Herren 2"})
    
    # Test CSV import
    csv_content = """team_id;team_name;penatly_created;penatly_user;penatly_reason;penatly_archived;penatly_paid;penatly_amount;penatly_currency;penatly_subject;search_params
298547;HSG WBW Herren 2;26-11-2024;Dennis Hirsch;Getränke;NO;;150;EUR;;search_user: Alle | search_type: TYPE_ALL | search_paid: FILTER_PAID_ALL | search_archived: STATUS_ALL"""
    
    response = client.post(
        "/import/1",
        files={"file": ("test.csv", csv_content, "text/csv")}
    )
    
    assert response.status_code == 200
    assert "Successfully imported" in response.text
    
    # Verify penalties were created
    response = client.get("/penalties/")
    assert "Dennis Hirsch" in response.text

def test_delete_penalty(client: TestClient):
    # Create test data
    client.post("/teams/", json={"name": "Test Team"})
    client.post("/users/", json={"full_name": "Test User", "team_id": 1})
    
    # Create penalty
    penalty_data = {
        "created_date": "2024-01-01",
        "reason": "Test Reason",
        "amount": 100.00,
        "user_id": 1,
        "team_id": 1
    }
    client.post("/penalties/", json=penalty_data)
    
    # Delete penalty
    response = client.delete("/penalties/1")
    assert response.status_code == 200
    
    # Verify deletion
    response = client.get("/penalties/")
    assert "Test Reason" not in response.text