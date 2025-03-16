from datetime import datetime
from typing import Optional, List
from pydantic import BaseModel, EmailStr, constr, confloat

# User schemas
class UserBase(BaseModel):
    name: constr(min_length=1, max_length=100)
    email: Optional[EmailStr] = None
    phone: Optional[str] = None

class UserCreate(UserBase):
    pass

class UserUpdate(BaseModel):
    name: Optional[constr(min_length=1, max_length=100)] = None
    email: Optional[EmailStr] = None
    phone: Optional[str] = None

class User(UserBase):
    id: str
    created_at: datetime
    updated_at: datetime

    class Config:
        orm_mode = True

# Penalty schemas
class PenaltyBase(BaseModel):
    user_id: str
    amount: confloat(gt=0)
    reason: Optional[str] = None
    date: Optional[datetime] = None

class PenaltyCreate(PenaltyBase):
    pass

class PenaltyUpdate(BaseModel):
    amount: Optional[confloat(gt=0)] = None
    reason: Optional[str] = None
    paid: Optional[bool] = None

class Penalty(PenaltyBase):
    penalty_id: str
    paid: bool
    paid_at: Optional[datetime]
    created_at: datetime
    updated_at: datetime

    class Config:
        orm_mode = True

# Transaction schemas
class TransactionBase(BaseModel):
    user_id: str
    amount: confloat(gt=0)
    description: Optional[str] = None
    transaction_date: Optional[datetime] = None

class TransactionCreate(TransactionBase):
    pass

class Transaction(TransactionBase):
    transaction_id: str
    created_at: datetime

    class Config:
        orm_mode = True

# Audit log schemas
class AuditLogBase(BaseModel):
    action: str
    entity_type: str
    entity_id: Optional[str] = None
    user_id: Optional[str] = None
    details: Optional[str] = None

class AuditLogCreate(AuditLogBase):
    pass

class AuditLog(AuditLogBase):
    log_id: str
    timestamp: datetime

    class Config:
        orm_mode = True

# Summary schemas
class PenaltySummary(BaseModel):
    total_count: int
    paid_count: int
    unpaid_count: int
    total_amount: float
    paid_amount: float
    unpaid_amount: float

class UserBalance(BaseModel):
    user_id: str
    total_unpaid: float

# Response schemas
class StandardResponse(BaseModel):
    success: bool
    message: str
    data: Optional[dict] = None

class ErrorResponse(BaseModel):
    success: bool = False
    error: str
    details: Optional[dict] = None
