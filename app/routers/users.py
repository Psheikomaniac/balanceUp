from fastapi import APIRouter, Depends, HTTPException, Query, Path, status
from sqlalchemy.orm import Session
from typing import List, Optional

from app.database import get_db
from app.database import crud, schemas
from app.utils.logging_config import get_logger
from app.errors.exceptions import ResourceNotFoundException

router = APIRouter(tags=["users"], prefix="/users")
logger = get_logger(__name__)

@router.post("/", response_model=schemas.UserResponse, status_code=status.HTTP_201_CREATED)
def create_user(user: schemas.UserCreate, db: Session = Depends(get_db)):
    """
    Create a new user
    """
    db_user = crud.get_user_by_email(db, email=user.email)
    if db_user:
        raise HTTPException(status_code=400, detail="Email already registered")
    
    return crud.create_user(db=db, user=user)

@router.get("/", response_model=List[schemas.UserResponse])
def read_users(
    skip: int = Query(0, ge=0, description="Skip N users"),
    limit: int = Query(100, ge=1, le=100, description="Limit the number of users returned"),
    search: Optional[str] = Query(None, description="Search users by name or email"),
    db: Session = Depends(get_db)
):
    """
    Get a list of users with optional search and pagination
    """
    users = crud.get_users(db, skip=skip, limit=limit, search=search)
    return users

@router.get("/{user_id}", response_model=schemas.UserWithPenalties)
def read_user(
    user_id: str = Path(..., description="The ID of the user to get"),
    db: Session = Depends(get_db)
):
    """
    Get detailed information about a specific user including their penalties
    """
    db_user = crud.get_user(db, user_id=user_id)
    if db_user is None:
        raise HTTPException(status_code=404, detail="User not found")
    return db_user

@router.put("/{user_id}", response_model=schemas.UserResponse)
def update_user(
    user_id: str = Path(..., description="The ID of the user to update"),
    user: schemas.UserUpdate = None,
    db: Session = Depends(get_db)
):
    """
    Update a user's information
    """
    user_dict = user.model_dump(exclude_unset=True) if user else {}
    updated_user = crud.update_user(db, user_id=user_id, user_data=user_dict)
    
    if updated_user is None:
        raise HTTPException(status_code=404, detail="User not found")
        
    return updated_user

@router.delete("/{user_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_user(
    user_id: str = Path(..., description="The ID of the user to delete"),
    db: Session = Depends(get_db)
):
    """
    Delete a user
    """
    result = crud.delete_user(db, user_id=user_id)
    if not result:
        raise HTTPException(status_code=404, detail="User not found")
    return None

@router.get("/{user_id}/penalties", response_model=List[schemas.PenaltyResponse])
def read_user_penalties(
    user_id: str = Path(..., description="The ID of the user"),
    include_paid: bool = Query(True, description="Whether to include paid penalties"),
    db: Session = Depends(get_db)
):
    """
    Get all penalties for a specific user
    """
    db_user = crud.get_user(db, user_id=user_id)
    if db_user is None:
        raise HTTPException(status_code=404, detail="User not found")
        
    penalties = crud.get_user_penalties(db, user_id=user_id, include_paid=include_paid)
    return penalties

@router.get("/{user_id}/balance", response_model=float)
def get_user_balance(
    user_id: str = Path(..., description="The ID of the user"),
    db: Session = Depends(get_db)
):
    """
    Get the total unpaid penalties balance for a user
    """
    db_user = crud.get_user(db, user_id=user_id)
    if db_user is None:
        raise HTTPException(status_code=404, detail="User not found")
        
    penalties = crud.get_user_penalties(db, user_id=user_id, include_paid=False)
    total = sum(penalty.amount for penalty in penalties)
    
    return total