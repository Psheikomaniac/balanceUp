from fastapi import APIRouter, Depends, HTTPException, Query, Path, status
from sqlalchemy.orm import Session
from typing import List, Optional

from app.database import get_db
from app.database import crud, schemas
from app.utils.logging_config import get_logger
from app.errors.exceptions import ResourceNotFoundException

router = APIRouter(tags=["penalties"], prefix="/penalties")
logger = get_logger(__name__)

@router.post("/", response_model=schemas.PenaltyResponse, status_code=status.HTTP_201_CREATED)
def create_penalty(
    penalty: schemas.PenaltyCreate,
    db: Session = Depends(get_db)
):
    """
    Create a new penalty
    """
    # Verify user exists
    user = crud.get_user(db, user_id=penalty.user_id)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"User with ID {penalty.user_id} not found"
        )
    
    return crud.create_penalty(db=db, penalty=penalty)

@router.get("/", response_model=List[schemas.PenaltyResponse])
def read_penalties(
    skip: int = Query(0, ge=0, description="Skip N penalties"),
    limit: int = Query(100, ge=1, le=100, description="Limit the number of penalties returned"),
    paid: Optional[bool] = Query(None, description="Filter by paid status"),
    db: Session = Depends(get_db)
):
    """
    Get a list of penalties with optional filtering and pagination
    """
    penalties = crud.get_penalties(db, skip=skip, limit=limit, paid=paid)
    return penalties

@router.get("/{penalty_id}", response_model=schemas.PenaltyResponse)
def read_penalty(
    penalty_id: str = Path(..., description="The ID of the penalty to get"),
    db: Session = Depends(get_db)
):
    """
    Get detailed information about a specific penalty
    """
    db_penalty = crud.get_penalty(db, penalty_id=penalty_id)
    if db_penalty is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Penalty not found"
        )
    return db_penalty

@router.put("/{penalty_id}", response_model=schemas.PenaltyResponse)
def update_penalty(
    penalty_id: str = Path(..., description="The ID of the penalty to update"),
    penalty: schemas.PenaltyUpdate = None,
    db: Session = Depends(get_db)
):
    """
    Update a penalty's information
    """
    penalty_dict = penalty.model_dump(exclude_unset=True) if penalty else {}
    updated_penalty = crud.update_penalty(db, penalty_id=penalty_id, penalty_data=penalty_dict)
    
    if updated_penalty is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Penalty not found"
        )
        
    return updated_penalty

@router.delete("/{penalty_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_penalty(
    penalty_id: str = Path(..., description="The ID of the penalty to delete"),
    db: Session = Depends(get_db)
):
    """
    Delete a penalty
    """
    result = crud.delete_penalty(db, penalty_id=penalty_id)
    if not result:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Penalty not found"
        )
    return None

@router.post("/{penalty_id}/mark-paid", response_model=schemas.PenaltyResponse)
def mark_penalty_as_paid(
    penalty_id: str = Path(..., description="The ID of the penalty to mark as paid"),
    db: Session = Depends(get_db)
):
    """
    Mark a specific penalty as paid
    """
    db_penalty = crud.mark_penalty_paid(db, penalty_id=penalty_id)
    if db_penalty is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Penalty not found"
        )
    return db_penalty

@router.get("/statistics/summary", response_model=dict)
def get_penalties_summary(db: Session = Depends(get_db)):
    """
    Get summary statistics about penalties
    """
    all_penalties = crud.get_penalties(db, skip=0, limit=1000)
    
    total_count = len(all_penalties)
    paid_count = sum(1 for p in all_penalties if p.paid)
    unpaid_count = total_count - paid_count
    
    total_amount = sum(p.amount for p in all_penalties)
    paid_amount = sum(p.amount for p in all_penalties if p.paid)
    unpaid_amount = total_amount - paid_amount
    
    return {
        "total_count": total_count,
        "paid_count": paid_count,
        "unpaid_count": unpaid_count,
        "total_amount": total_amount,
        "paid_amount": paid_amount,
        "unpaid_amount": unpaid_amount
    }
