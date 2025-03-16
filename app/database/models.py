import os
from datetime import datetime
from typing import List, Optional
from uuid import uuid4

from sqlalchemy import Column, String, Float, Boolean, DateTime, ForeignKey, Text, create_engine
from sqlalchemy.orm import relationship
from sqlalchemy.ext.declarative import declarative_base

from app.database import Base

Base = declarative_base()

class User(Base):
    """User model for storing user information"""
    __tablename__ = "users"
    
    id = Column(String(36), primary_key=True, index=True, default=lambda: str(uuid4()))
    name = Column(String(100), index=True, nullable=False)
    email = Column(String(100), unique=True, index=True, nullable=True)
    phone = Column(String(20), nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    penalties = relationship("Penalty", back_populates="user", cascade="all, delete-orphan")
    transactions = relationship("Transaction", back_populates="user")
    
    def __repr__(self) -> str:
        return f"<User(id={self.id}, name={self.name})>"
    
    @property
    def total_unpaid_penalties(self) -> float:
        """Calculate total unpaid penalties for this user"""
        return sum(penalty.amount for penalty in self.penalties if not penalty.paid)
    
    @property
    def total_paid_penalties(self) -> float:
        """Calculate total paid penalties for this user"""
        return sum(penalty.amount for penalty in self.penalties if penalty.paid)

class Penalty(Base):
    """Penalty model for storing user penalties"""
    __tablename__ = "penalties"
    
    penalty_id = Column(String(36), primary_key=True, index=True, default=lambda: str(uuid4()))
    user_id = Column(String(36), ForeignKey("users.id", ondelete="CASCADE"), index=True, nullable=False)
    amount = Column(Float, nullable=False)
    reason = Column(Text, nullable=True)
    date = Column(DateTime, default=datetime.utcnow)
    paid = Column(Boolean, default=False)
    paid_at = Column(DateTime, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    user = relationship("User", back_populates="penalties")
    
    def __repr__(self) -> str:
        return f"<Penalty(id={self.penalty_id}, user={self.user_id}, amount={self.amount}, paid={self.paid})>"
    
    def mark_as_paid(self) -> None:
        """Mark this penalty as paid"""
        self.paid = True
        self.paid_at = datetime.utcnow()

class Transaction(Base):
    """Transaction model for storing payment transactions"""
    __tablename__ = "transactions"
    
    transaction_id = Column(String(36), primary_key=True, index=True, default=lambda: str(uuid4()))
    user_id = Column(String(36), ForeignKey("users.id", ondelete="CASCADE"), index=True, nullable=False)
    amount = Column(Float, nullable=False)
    transaction_date = Column(DateTime, default=datetime.utcnow)
    description = Column(Text, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    
    # Relationships
    user = relationship("User", back_populates="transactions")
    
    def __repr__(self) -> str:
        return f"<Transaction(id={self.transaction_id}, user={self.user_id}, amount={self.amount})>"

class AuditLog(Base):
    """Audit log for tracking important system activities"""
    __tablename__ = "audit_logs"
    
    log_id = Column(String(36), primary_key=True, index=True, default=lambda: str(uuid4()))
    action = Column(String(50), nullable=False)
    entity_type = Column(String(50), nullable=False)
    entity_id = Column(String(36), nullable=True)
    user_id = Column(String(36), ForeignKey("users.id"), nullable=True)
    details = Column(Text, nullable=True)
    timestamp = Column(DateTime, default=datetime.utcnow)
    
    # Relationships
    user = relationship("User")
    
    def __repr__(self) -> str:
        return f"<AuditLog(id={self.log_id}, action={self.action}, entity={self.entity_type})>"

def get_engine():
    """Get SQLAlchemy engine"""
    from app.config.settings import get_settings
    settings = get_settings()
    
    # Ensure database directory exists
    if not settings.DATABASE_URL.startswith("sqlite:///:memory:"):
        db_dir = os.path.dirname(settings.DATABASE_URL.replace('sqlite:///', ''))
        os.makedirs(db_dir, exist_ok=True)
    
    return create_engine(
        settings.DATABASE_URL,
        connect_args={"check_same_thread": False}
    )

def init_db():
    """Initialize the database"""
    engine = get_engine()
    Base.metadata.create_all(bind=engine)
    return engine
