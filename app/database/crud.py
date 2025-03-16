from sqlalchemy.orm import Session, sessionmaker
from datetime import datetime
from . import models, schemas
from typing import List, Optional
from sqlalchemy import desc
from app.config.settings import get_settings

settings = get_settings()
_SessionLocal = None

def get_db():
    """Get database session"""
    global _SessionLocal
    if _SessionLocal is None:
        from app.database.models import get_engine
        engine = get_engine()
        _SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    
    db = _SessionLocal()
    try:
        yield db
    finally:
        db.close()

# User operations
def get_user(db: Session, user_id: int) -> Optional[models.User]:
    return db.query(models.User).filter(models.User.id == user_id).first()

def get_user_by_email(db: Session, email: str) -> Optional[models.User]:
    return db.query(models.User).filter(models.User.email == email).first()

def get_users(db: Session, skip: int = 0, limit: int = 100) -> List[models.User]:
    return db.query(models.User).offset(skip).limit(limit).all()

def create_user(db: Session, user: schemas.UserCreate) -> models.User:
    db_user = models.User(
        username=user.username,
        email=user.email
    )
    db.add(db_user)
    db.commit()
    db.refresh(db_user)
    return db_user

# Penalty operations
def create_penalty(db: Session, penalty: schemas.PenaltyCreate) -> models.Penalty:
    db_penalty = models.Penalty(
        user_id=penalty.user_id,
        amount=penalty.amount,
        reason=penalty.reason,
        paid=False
    )
    db.add(db_penalty)
    db.commit()
    db.refresh(db_penalty)
    return db_penalty

def get_user_penalties(db: Session, user_id: int) -> List[models.Penalty]:
    return db.query(models.Penalty)\
        .filter(models.Penalty.user_id == user_id)\
        .order_by(desc(models.Penalty.created_at))\
        .all()

def mark_penalty_paid(db: Session, penalty_id: int) -> Optional[models.Penalty]:
    penalty = db.query(models.Penalty).filter(models.Penalty.id == penalty_id).first()
    if penalty:
        penalty.paid = True
        penalty.paid_at = datetime.utcnow()
        db.commit()
        db.refresh(penalty)
    return penalty
