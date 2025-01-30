from sqlmodel import SQLModel, Field, Relationship
from datetime import date
from typing import Optional
from decimal import Decimal

class PenaltyBase(SQLModel):
    created_date: date = Field(default=date.today())
    reason: str
    amount: Decimal = Field(max_digits=10, decimal_places=2)
    currency: str = "EUR"
    paid_date: Optional[date] = None  # Ensure this field exists
    user_id: int = Field(foreign_key="user.id")
    team_id: int = Field(foreign_key="team.team_id")

class Penalty(PenaltyBase, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    user: "User" = Relationship(back_populates="penalties")
    team: "Team" = Relationship(back_populates="penalties")