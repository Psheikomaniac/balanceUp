from fastapi import APIRouter, Depends, HTTPException, Request, Query, Path
from sqlalchemy.orm import Session
from typing import List, Optional
from datetime import datetime

from app.database import get_db
from app.database.models import User
from app.database.schemas import UserCreate, UserResponse, UserUpdate, UserWithPenalties
from app.middleware.rate_limiter import rate_limit
from app.services.user_utils import UserUtils
from app.utils.logging_config import get_logger

logger = get_logger(__name__)
router = APIRouter(tags=["users"])

@router.post("/", response_model=UserResponse, status_code=201)
@rate_limit()
async def create_user(
    request: Request, 
    user: UserCreate, 
    db: Session = Depends(get_db)
):
    """
    Create a new user
    """
    try:
        # Check if user with same email exists
        if user.email:
            existing_user = db.query(User).filter(User.email == user.email).first()
            if existing_user:
                logger.warning(f"Attempt to create user with existing email: {user.email}")
                raise HTTPException(status_code=400, detail="Email already registered")
        
        # Check if user with same name exists
        existing_user = db.query(User).filter(User.name == user.name).first()
        if existing_user:
            logger.warning(f"Attempt to create user with existing name: {user.name}")
            raise HTTPException(status_code=400, detail="Username already registered")
            
        # Create user
        new_user = User(
            name=user.name,
            email=user.email,
            phone=user.phone
        )
        
        db.add(new_user)
        db.commit()
        db.refresh(new_user)
        
        logger.info(f"Created new user: {new_user.name} (ID: {new_user.id})")
        return new_user
        
    except Exception as e:
        db.rollback()
        logger.error(f"Error creating user: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Failed to create user: {str(e)}")

@router.get("/", response_model=List[UserResponse])
@rate_limit()
async def list_users(
    request: Request,
    skip: int = Query(0, ge=0, description="Number of records to skip"),
    limit: int = Query(100, ge=1, le=100, description="Maximum number of records to return"),
    search: Optional[str] = Query(None, description="Search by name or email"),
    db: Session = Depends(get_db)
):
    """
    Get a list of users with optional search and pagination
    """
    try:
        query = db.query(User)
        
        # Apply search filter if provided
        if search:
            search_term = f"%{search}%"
            query = query.filter(
                (User.name.ilike(search_term)) | 
                (User.email.ilike(search_term))
            )
            
        # Apply pagination
        users = query.offset(skip).limit(limit).all()
        
        logger.info(f"Retrieved {len(users)} users (skip={skip}, limit={limit}, search={search})")
        return users
        
    except Exception as e:
        logger.error(f"Error retrieving users: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Failed to retrieve users: {str(e)}")

@router.get("/{user_id}", response_model=UserResponse)
@rate_limit()
async def get_user(
    request: Request,
    user_id: str = Path(..., description="User ID"),
    db: Session = Depends(get_db)
):
    """
    Get a specific user by ID
    """
    try:
        user = UserUtils.get_user_by_id(db, user_id=user_id)
        if not user:
            logger.warning(f"User not found: {user_id}")
            raise HTTPException(status_code=404, detail="User not found")
            
        logger.info(f"Retrieved user: {user.name} (ID: {user_id})")
        return user
        
    except Exception as e:
        logger.error(f"Error retrieving user {user_id}: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Failed to retrieve user: {str(e)}")

@router.get("/{user_id}/with-penalties", response_model=UserWithPenalties)
@rate_limit()
async def get_user_with_penalties(
    request: Request,
    user_id: str = Path(..., description="User ID"),
    include_paid: bool = Query(True, description="Include paid penalties"),
    db: Session = Depends(get_db)
):
    """
    Get a user with all their penalties
    """
    try:
        user = UserUtils.get_user_by_id(db, user_id=user_id)
        if not user:
            logger.warning(f"User not found: {user_id}")
            raise HTTPException(status_code=404, detail="User not found")
            
        # Filter penalties if needed
        if not include_paid:
            penalties = [p for p in user.penalties if not p.paid]
            user.penalties = penalties
        
        logger.info(f"Retrieved user with {len(user.penalties)} penalties: {user.name} (ID: {user_id})")
        return user
        
    except Exception as e:
        logger.error(f"Error retrieving user with penalties {user_id}: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Failed to retrieve user with penalties: {str(e)}")

@router.patch("/{user_id}", response_model=UserResponse)
@rate_limit()
async def update_user(
    request: Request,
    user_id: str = Path(..., description="User ID"),
    user_update: UserUpdate = ...,
    db: Session = Depends(get_db)
):
    """
    Update user information
    """
    try:
        user = UserUtils.get_user_by_id(db, user_id=user_id)
        if not user:
            logger.warning(f"Attempt to update non-existent user: {user_id}")
            raise HTTPException(status_code=404, detail="User not found")
            
        # Check if email is being updated and is already taken
        if user_update.email and user_update.email != user.email:
            existing_user = db.query(User).filter(User.email == user_update.email).first()
            if existing_user:
                logger.warning(f"Attempt to update user with existing email: {user_update.email}")
                raise HTTPException(status_code=400, detail="Email already registered")
                
        # Check if name is being updated and is already taken
        if user_update.name and user_update.name != user.name:
            existing_user = db.query(User).filter(User.name == user_update.name).first()
            if existing_user:
                logger.warning(f"Attempt to update user with existing name: {user_update.name}")
                raise HTTPException(status_code=400, detail="Username already registered")
                
        # Update fields if provided
        if user_update.name:
            user.name = user_update.name
        if user_update.email:
            user.email = user_update.email
        if user_update.phone:
            user.phone = user_update.phone
            
        user.updated_at = datetime.utcnow()
        
        db.commit()
        db.refresh(user)
        
        logger.info(f"Updated user: {user.name} (ID: {user_id})")
        return user
        
    except Exception as e:
        db.rollback()
        logger.error(f"Error updating user {user_id}: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Failed to update user: {str(e)}")

@router.delete("/{user_id}", status_code=204)
@rate_limit()
async def delete_user(
    request: Request,
    user_id: str = Path(..., description="User ID"),
    db: Session = Depends(get_db)
):
    """
    Delete a user
    """
    try:
        user = UserUtils.get_user_by_id(db, user_id=user_id)
        if not user:
            logger.warning(f"Attempt to delete non-existent user: {user_id}")
            raise HTTPException(status_code=404, detail="User not found")
            
        db.delete(user)
        db.commit()
        
        logger.info(f"Deleted user: {user.name} (ID: {user_id})")
        
    except Exception as e:
        db.rollback()
        logger.error(f"Error deleting user {user_id}: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Failed to delete user: {str(e)}")

@router.get("/{user_id}/balance", response_model=dict)
@rate_limit()
async def get_user_balance(
    request: Request,
    user_id: str = Path(..., description="User ID"),
    db: Session = Depends(get_db)
):
    """
    Get a user's current balance (sum of unpaid penalties)
    """
    try:
        balance = UserUtils.get_user_balance(db, user_id=user_id)
        
        logger.info(f"Retrieved balance for user {user_id}: {balance}")
        return {"user_id": user_id, "balance": balance}
        
    except Exception as e:
        logger.error(f"Error retrieving balance for user {user_id}: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Failed to retrieve user balance: {str(e)}")