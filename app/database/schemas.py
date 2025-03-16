from __future__ import annotations
import re
from datetime import datetime
from typing import Optional, List
from pydantic import BaseModel, EmailStr, Field, field_validator, ConfigDict
from uuid import UUID
from decimal import Decimal

# Base models configurations
model_config = ConfigDict(from_attributes=True)

class PenaltyBase(BaseModel):
    user_id: str = Field(..., description="ID of the user who received the penalty")
    amount: Decimal = Field(..., gt=0, description="Penalty amount (must be positive)")
    reason: Optional[str] = Field(None, description="Reason for the penalty")
    date: Optional[datetime] = Field(default_factory=datetime.utcnow, description="When the penalty was issued")

    @field_validator('user_id')
    def validate_uuid(cls, v):
        if v and not re.match(r'^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$', v):
            raise ValueError('Invalid UUID format')
        return v

class Penalty(PenaltyBase):
    model_config = model_config
    
    penalty_id: str
    paid: bool = Field(False, description="Whether the penalty has been paid")
    paid_at: Optional[datetime] = Field(None, description="When the penalty was paid")
    created_at: datetime
    updated_at: datetime

class UserBase(BaseModel):
    name: str = Field(..., min_length=1, max_length=100, description="User's full name")
    email: Optional[EmailStr] = Field(None, description="User's email address")
    phone: Optional[str] = Field(None, description="Phone number in international format")

    @field_validator('phone')
    def validate_phone(cls, v):
        if v and not re.match(r'^\+?1?\d{9,15}$', v):
            raise ValueError('Invalid phone number format')
        return v

class User(UserBase):
    model_config = model_config
    
    id: str = Field(..., description="Unique user identifier")
    created_at: datetime
    updated_at: datetime
    total_unpaid_penalties: float = Field(0.0, description="Sum of all unpaid penalties")
    total_paid_penalties: float = Field(0.0, description="Sum of all paid penalties")

class UserResponse(User):
    """Response model for user endpoints"""
    model_config = model_config

class UserWithPenalties(User):
    """Response model for detailed user information including penalties"""
    model_config = model_config
    penalties: List[Penalty]

class UserCreate(UserBase):
    pass

class UserUpdate(BaseModel):
    name: Optional[str] = Field(None, min_length=1, max_length=100)
    email: Optional[EmailStr] = None
    phone: Optional[str] = None

    @field_validator('phone')
    def validate_phone(cls, v):
        if v and not re.match(r'^\+?1?\d{9,15}$', v):
            raise ValueError('Invalid phone number format')
        return v

class PenaltyCreate(PenaltyBase):
    pass

class PenaltyUpdate(BaseModel):
    amount: Optional[Decimal] = Field(None, gt=0)
    reason: Optional[str] = None
    paid: Optional[bool] = None

class PenaltyResponse(Penalty):
    """Response model for penalty endpoints"""
    model_config = model_config
    user: UserResponse

class TransactionBase(BaseModel):
    user_id: str = Field(..., description="ID of the user making the transaction")
    amount: Decimal = Field(..., gt=0, description="Transaction amount (must be positive)")
    description: Optional[str] = Field(None, description="Transaction description")
    transaction_date: Optional[datetime] = Field(
        default_factory=datetime.utcnow,
        description="When the transaction occurred"
    )

    @field_validator('user_id')
    def validate_uuid(cls, v):
        try:
            UUID(v)
            return v
        except ValueError:
            raise ValueError('Invalid UUID format')

    @field_validator('amount')
    def validate_amount(cls, v):
        if v <= 0:
            raise ValueError('Amount must be greater than 0')
        return v

class TransactionCreate(TransactionBase):
    pass

class Transaction(TransactionBase):
    model_config = model_config
    
    transaction_id: str
    created_at: datetime

class AuditLogBase(BaseModel):
    action: str = Field(..., min_length=1, description="The action that was performed")
    entity_type: str = Field(..., description="The type of entity the action was performed on")
    entity_id: Optional[str] = Field(None, description="ID of the affected entity")
    user_id: Optional[str] = Field(None, description="ID of the user who performed the action")
    details: Optional[str] = Field(None, description="Additional details about the action")

class AuditLogCreate(AuditLogBase):
    pass

class AuditLog(AuditLogBase):
    model_config = model_config
    
    log_id: str
    timestamp: datetime

class PenaltySummary(BaseModel):
    total_count: int = Field(..., description="Total number of penalties")
    paid_count: int = Field(..., description="Number of paid penalties")
    unpaid_count: int = Field(..., description="Number of unpaid penalties")
    total_amount: Decimal = Field(..., description="Total amount of all penalties")
    paid_amount: Decimal = Field(..., description="Total amount of paid penalties")
    unpaid_amount: Decimal = Field(..., description="Total amount of unpaid penalties")

class UserBalance(BaseModel):
    user_id: str = Field(..., description="User ID")
    total_unpaid: Decimal = Field(..., description="Total amount of unpaid penalties")

class StandardResponse(BaseModel):
    success: bool = Field(..., description="Whether the operation was successful")
    message: str = Field(..., description="Response message")
    data: Optional[dict] = Field(None, description="Response data")

class ErrorResponse(BaseModel):
    success: bool = Field(False, description="Operation failed")
    error: str = Field(..., description="Error message")
    details: Optional[dict] = Field(None, description="Additional error details")
