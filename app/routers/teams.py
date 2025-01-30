from fastapi import APIRouter, Depends, HTTPException
from sqlmodel import Session
from app.models import Team
from app.database import get_db

router = APIRouter()

@router.post("/", response_model=Team)
def create_team(team: Team, db: Session = Depends(get_db)):
    db.add(team)
    db.commit()
    db.refresh(team)
    return team

@router.get("/")
def read_teams(skip: int = 0, limit: int = 100, db: Session = Depends(get_db)):
    teams = db.query(Team).offset(skip).limit(limit).all()
    return teams