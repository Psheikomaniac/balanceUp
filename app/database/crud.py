from sqlalchemy.orm import Session, sessionmaker
from datetime import datetime
from typing import List, Optional, Dict, Any
import uuid

from app.database import models
from app.database import schemas
from app.utils.logging_config import get_logger
from sqlalchemy import desc, or_, and_, func
from app.config.settings import get_settings

settings = get_settings()
_SessionLocal = None

logger = get_logger(__name__)

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
def get_user(db: Session, user_id: str) -> Optional[models.User]:
    """Get a user by ID"""
    return db.query(models.User).filter(models.User.id == user_id).first()

def get_user_by_email(db: Session, email: str) -> Optional[models.User]:
    """Get a user by email"""
    return db.query(models.User).filter(models.User.email == email).first()

def get_user_by_name(db: Session, name: str) -> Optional[models.User]:
    """Get a user by name"""
    return db.query(models.User).filter(models.User.name == name).first()

def get_users(db: Session, skip: int = 0, limit: int = 100, search: Optional[str] = None) -> List[models.User]:
    """Get a list of users with optional search and pagination"""
    query = db.query(models.User)
    
    if search:
        search_term = f"%{search}%"
        query = query.filter(
            (models.User.name.ilike(search_term)) | 
            (models.User.email.ilike(search_term))
        )
        
    return query.offset(skip).limit(limit).all()

def create_user(db: Session, user: schemas.UserCreate) -> models.User:
    """Create a new user"""
    db_user = models.User(
        id=str(uuid.uuid4()),
        name=user.name,
        email=user.email,
        phone=user.phone,
        created_at=datetime.utcnow(),
        updated_at=datetime.utcnow()
    )
    db.add(db_user)
    db.commit()
    db.refresh(db_user)
    logger.info(f"Created new user: {db_user.name} (ID: {db_user.id})")
    return db_user

def update_user(db: Session, user_id: str, user_data: Dict[str, Any]) -> Optional[models.User]:
    """Update an existing user"""
    db_user = get_user(db, user_id)
    if not db_user:
        return None
        
    for key, value in user_data.items():
        if hasattr(db_user, key) and key != 'id':  # Don't update ID
            setattr(db_user, key, value)
            
    db_user.updated_at = datetime.utcnow()
    db.commit()
    db.refresh(db_user)
    logger.info(f"Updated user: {db_user.name} (ID: {db_user.id})")
    return db_user

def delete_user(db: Session, user_id: str) -> bool:
    """Delete a user"""
    db_user = get_user(db, user_id)
    if not db_user:
        return False
        
    db.delete(db_user)
    db.commit()
    logger.info(f"Deleted user with ID: {user_id}")
    return True

# Penalty operations
def get_penalty(db: Session, penalty_id: str) -> Optional[models.Penalty]:
    """Get a penalty by ID"""
    return db.query(models.Penalty).filter(models.Penalty.penalty_id == penalty_id).first()

def get_penalties(db: Session, skip: int = 0, limit: int = 100, paid: Optional[bool] = None) -> List[models.Penalty]:
    """Get a list of penalties with optional filtering and pagination"""
    query = db.query(models.Penalty)
    
    if paid is not None:
        query = query.filter(models.Penalty.paid == paid)
        
    return query.offset(skip).limit(limit).all()

def get_user_penalties(db: Session, user_id: str, include_paid: bool = True) -> List[models.Penalty]:
    """Get penalties for a specific user"""
    query = db.query(models.Penalty).filter(models.Penalty.user_id == user_id)
    
    if not include_paid:
        query = query.filter(models.Penalty.paid == False)
        
    return query.all()

def create_penalty(db: Session, penalty: schemas.PenaltyCreate) -> models.Penalty:
    """Create a new penalty"""
    db_penalty = models.Penalty(
        penalty_id=str(uuid.uuid4()),
        user_id=penalty.user_id,
        amount=penalty.amount,
        reason=penalty.reason,
        date=penalty.date or datetime.utcnow(),
        paid=False,
        created_at=datetime.utcnow(),
        updated_at=datetime.utcnow()
    )
    db.add(db_penalty)
    db.commit()
    db.refresh(db_penalty)
    logger.info(f"Created new penalty for user {penalty.user_id}: {db_penalty.penalty_id}")
    return db_penalty

def update_penalty(db: Session, penalty_id: str, penalty_data: Dict[str, Any]) -> Optional[models.Penalty]:
    """Update an existing penalty"""
    db_penalty = get_penalty(db, penalty_id)
    if not db_penalty:
        return None
        
    for key, value in penalty_data.items():
        if hasattr(db_penalty, key) and key != 'penalty_id':  # Don't update ID
            setattr(db_penalty, key, value)
            
    # If marking as paid, set paid_at timestamp
    if 'paid' in penalty_data and penalty_data['paid'] and not db_penalty.paid_at:
        db_penalty.paid_at = datetime.utcnow()
    elif 'paid' in penalty_data and not penalty_data['paid']:
        db_penalty.paid_at = None
        
    db_penalty.updated_at = datetime.utcnow()
    db.commit()
    db.refresh(db_penalty)
    logger.info(f"Updated penalty: {db_penalty.penalty_id}")
    return db_penalty

def mark_penalty_paid(db: Session, penalty_id: str) -> Optional[models.Penalty]:
    """Mark a penalty as paid"""
    db_penalty = get_penalty(db, penalty_id)
    if not db_penalty:
        return None
        
    db_penalty.mark_as_paid()
    db.commit()
    db.refresh(db_penalty)
    logger.info(f"Marked penalty as paid: {db_penalty.penalty_id}")
    return db_penalty

def delete_penalty(db: Session, penalty_id: str) -> bool:
    """Delete a penalty"""
    db_penalty = get_penalty(db, penalty_id)
    if not db_penalty:
        return False
        
    db.delete(db_penalty)
    db.commit()
    logger.info(f"Deleted penalty with ID: {penalty_id}")
    return True

def get_penalties_summary(db: Session) -> Dict[str, Any]:
    """Get summary statistics for penalties."""
    total_penalties = db.query(models.Penalty).count()
    paid_penalties = db.query(models.Penalty).filter(models.Penalty.paid == True).count()
    
    total_amount = db.query(func.sum(models.Penalty.amount)).scalar() or 0
    paid_amount = db.query(func.sum(models.Penalty.amount))\
        .filter(models.Penalty.paid == True).scalar() or 0
    
    return {
        "total_count": total_penalties,
        "paid_count": paid_penalties,
        "unpaid_count": total_penalties - paid_penalties,
        "total_amount": float(total_amount),
        "paid_amount": float(paid_amount),
        "unpaid_amount": float(total_amount - paid_amount)
    }

# Transaction operations
def create_transaction(db: Session, transaction: schemas.TransactionCreate) -> models.Transaction:
    """Create a new transaction"""
    db_transaction = models.Transaction(
        transaction_id=str(uuid.uuid4()),
        user_id=transaction.user_id,
        amount=transaction.amount,
        description=transaction.description,
        transaction_date=transaction.transaction_date or datetime.utcnow(),
        created_at=datetime.utcnow()
    )
    db.add(db_transaction)
    db.commit()
    db.refresh(db_transaction)
    logger.info(f"Created new transaction for user {transaction.user_id}: {db_transaction.transaction_id}")
    return db_transaction

def get_user_transactions(db: Session, user_id: str) -> List[models.Transaction]:
    """Get transactions for a specific user"""
    return db.query(models.Transaction).filter(models.Transaction.user_id == user_id).all()

def get_transaction(db: Session, transaction_id: str) -> Optional[models.Transaction]:
    """Get a transaction by ID."""
    return db.query(models.Transaction)\
        .filter(models.Transaction.transaction_id == transaction_id).first()

def get_user_transactions(db: Session, user_id: str, skip: int = 0, limit: int = 100) -> List[models.Transaction]:
    """Get all transactions for a specific user."""
    return db.query(models.Transaction)\
        .filter(models.Transaction.user_id == user_id)\
        .offset(skip).limit(limit).all()

# Audit logging
def create_audit_log(db: Session, log_entry: schemas.AuditLogCreate) -> models.AuditLog:
    """Create a new audit log entry"""
    db_log = models.AuditLog(
        log_id=str(uuid.uuid4()),
        action=log_entry.action,
        entity_type=log_entry.entity_type,
        entity_id=log_entry.entity_id,
        user_id=log_entry.user_id,
        details=log_entry.details,
        timestamp=datetime.utcnow()
    )
    db.add(db_log)
    db.commit()
    db.refresh(db_log)
    return db_log

def get_audit_logs(
    db: Session,
    entity_type: Optional[str] = None,
    entity_id: Optional[str] = None,
    user_id: Optional[str] = None,
    skip: int = 0,
    limit: int = 100
) -> List[models.AuditLog]:
    """Get audit logs with optional filters."""
    query = db.query(models.AuditLog)
    
    if entity_type:
        query = query.filter(models.AuditLog.entity_type == entity_type)
    if entity_id:
        query = query.filter(models.AuditLog.entity_id == entity_id)
    if user_id:
        query = query.filter(models.AuditLog.user_id == user_id)
    
    return query.order_by(models.AuditLog.timestamp.desc())\
        .offset(skip).limit(limit).all()

def get_user_balance(db: Session, user_id: str) -> float:
    """Calculate a user's current balance (sum of unpaid penalties)."""
    total_penalties = db.query(func.sum(models.Penalty.amount))\
        .filter(
            and_(
                models.Penalty.user_id == user_id,
                models.Penalty.paid == False
            )
        ).scalar() or 0.0
    
    return float(total_penalties)

def pay_penalty(db: Session, penalty_id: str) -> Optional[models.Transaction]:
    """Pay a penalty and create a transaction record."""
    db_penalty = get_penalty(db, penalty_id)
    if not db_penalty or db_penalty.paid:
        return None
    
    # Create transaction
    transaction = create_transaction(
        db,
        schemas.TransactionCreate(
            user_id=db_penalty.user_id,
            amount=db_penalty.amount,
            description=f"Payment for penalty: {db_penalty.reason or penalty_id}"
        )
    )
    
    # Mark penalty as paid
    mark_penalty_paid(db, penalty_id)
    
    return transaction
