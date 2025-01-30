from sqlmodel import SQLModel, Field, Relationship
from typing import List, Optional

class TeamBase(SQLModel):
    name: str = Field(index=True, unique=True)

class Team(TeamBase, table=True):
    team_id: Optional[int] = Field(default=None, primary_key=True)
    users: List["User"] = Relationship(back_populates="team")
    penalties: List["Penalty"] = Relationship(back_populates="team")