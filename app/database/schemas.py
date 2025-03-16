from pydantic import BaseModel, Field, validator
from typing import Optional, List
from datetime import datetime
import uuid

class PenaltyBase(BaseModel):
    """Base model for penalty data"""
    amount: float = Field(..., gt=0, description="Penalty amount (must be greater than 0)")
    reason: Optional[str] = Field(None, description="Reason for the penalty")
    date: Optional[datetime] = Field(None, description="Date when the penalty was issued")

class PenaltyCreate(PenaltyBase):
    """Model for creating a penalty"""
    user_id: str = Field(..., description="ID of the user who received the penalty")

class PenaltyUpdate(BaseModel):
    """Model for updating a penalty"""
    amount: Optional[float] = Field(None, gt=0, description="Updated penalty amount")
    reason: Optional[str] = Field(None, description="Updated reason for the penalty")
    date: Optional[datetime] = Field(None, description="Updated date of the penalty")
    paid: Optional[bool] = Field(None, description="Whether the penalty has been paid")

    @validator('amount')
    def amount_must_be_positive(cls, v):
        if v is not None and v <= 0:
            raise ValueError('Amount must be greater than 0')
        return v

class PenaltyResponse(PenaltyBase):
    """Model for penalty responses"""
    penalty_id: str
    user_id: str
    paid: bool
    paid_at: Optional[datetime] = None
    created_at: datetime
    updated_at: datetime

    class Config:
        orm_mode = True
        
class UserBase(BaseModel):
    """Base model for user data"""
    name: str = Field(..., min_length=1, max_length=100, description="User's name")
    email: Optional[str] = Field(None, description="User's email address")
    phone: Optional[str] = Field(None, description="User's phone number")

class UserCreate(UserBase):
    """Model for creating a user"""
    pass

class UserUpdate(BaseModel):
    """Model for updating a user"""
    name: Optional[str] = Field(None, min_length=1, max_length=100, description="Updated name")
    email: Optional[str] = Field(None, description="Updated email address")
    phone: Optional[str] = Field(None, description="Updated phone number")

class UserResponse(UserBase):
    """Model for user responses"""
    id: str
    created_at: datetime
    updated_at: datetime
    
    class Config:
        orm_mode = True

class UserWithPenalties(UserResponse):
    """User model with penalties included"""
    penalties: List[PenaltyResponse] = []
    
    class Config:
        orm_mode = True

class TransactionBase(BaseModel):
    """Base model for transaction data"""
    amount: float = Field(..., gt=0, description="Transaction amount")
    description: Optional[str] = Field(None, description="Transaction description")
    transaction_date: Optional[datetime] = Field(None, description="Transaction date")

class TransactionCreate(TransactionBase):
    """Model for creating a transaction"""
    user_id: str = Field(..., description="ID of the user associated with the transaction")

class TransactionResponse(TransactionBase):
    """Model for transaction responses"""
    transaction_id: str
    user_id: str
    created_at: datetime
    
    class Config:
        orm_mode = True
