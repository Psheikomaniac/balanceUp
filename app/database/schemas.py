from pydantic import BaseModel
from typing import Optional

class Penalty(BaseModel):
    penalty_id: str
    user_id: int
    team_id: int
    penalty_created: str
    penalty_reason: str
    penalty_archived: str
    penalty_amount: float
    penalty_currency: str
    penalty_subject: Optional[str] = None
    search_params: Optional[str] = None
    penalty_paid_date: Optional[str] = None

    class Config:
        from_attributes = True

class User(BaseModel):
    user_id: int
    user_name: str
    team_id: int

    class Config:
        from_attributes = True
