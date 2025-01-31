from sqlmodel import SQLModel, Field, Relationship
from typing import List, Optional
from pydantic import computed_field
from app.models import Team

class UserBase(SQLModel):
    full_name: str = Field(index=True)
    team_id: int = Field(foreign_key="team.team_id")

class User(UserBase, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    team: "Team" = Relationship(back_populates="users")
    penalties: List["Penalty"] = Relationship(back_populates="user")

class UserRead(UserBase):
    id: int
    total_debt: float
    total_credit: float
    balance: float

    @computed_field
    @property
    def balance_status(self) -> str:
        return "overdue" if self.balance > 0 else "credit"