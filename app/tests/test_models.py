from app.models import Team, User, Penalty
from sqlmodel import SQLModel
from datetime import date
from decimal import Decimal

def test_create_models():
    team = Team(name="Test Team")
    user = User(full_name="Test User", team_id=1)
    penalty = Penalty(
        created_date=date.today(),
        reason="Test Reason",
        amount=Decimal("100.00"),
        user_id=1,
        team_id=1
    )
    
    assert team.name == "Test Team"
    assert user.full_name == "Test User"
    assert penalty.amount == 100.00