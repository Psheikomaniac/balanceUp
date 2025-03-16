from fastapi import APIRouter, Depends, HTTPException, Request, Query, Path
from sqlalchemy.orm import Session
from typing import List, Optional
from datetime import datetime

from app.database import get_db
from app.database.models import Penalty, User
from app.database.schemas import PenaltyCreate, PenaltyResponse, PenaltyUpdate
from app.middleware.rate_limiter import rate_limit
from app.services.user_utils import UserUtils
from app.utils.logging_config import get_logger
from app.errors.exceptions import ResourceNotFoundException

logger = get_logger(__name__)
router = APIRouter(tags=["penalties"])

@router.post("/", response_model=PenaltyResponse, status_code=201)
@rate_limit()
async def create_penalty(
    request: Request, 
    penalty: PenaltyCreate, 
    db: Session = Depends(get_db)
):
    """
    Create a new penalty for a user
    """
    try:
        # Verify user exists
        user = UserUtils.get_user_by_id(db, user_id=penalty.user_id)
        if not user:
            logger.warning(f"Attempt to create penalty for non-existent user: {penalty.user_id}")
            raise HTTPException(status_code=404, detail="User not found")
            
        # Create the penalty
        new_penalty = Penalty(
            user_id=penalty.user_id,
            amount=penalty.amount,
            reason=penalty.reason,
            date=penalty.date or datetime.utcnow(),
            paid=False
        )
        
        db.add(new_penalty)
        db.commit()
        db.refresh(new_penalty)
        
        logger.info(f"Created new penalty for user {penalty.user_id}: {new_penalty.penalty_id}")
        return new_penalty
        
    except Exception as e:
        db.rollback()
        logger.error(f"Error creating penalty: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Failed to create penalty: {str(e)}")

@router.get("/", response_model=List[PenaltyResponse])
@rate_limit()
async def get_all_penalties(
    request: Request,
    skip: int = Query(0, ge=0, description="Number of records to skip"),
    limit: int = Query(100, ge=1, le=100, description="Maximum number of records to return"),
    paid: Optional[bool] = Query(None, description="Filter by paid status"),
    db: Session = Depends(get_db)
):
    """
    Get all penalties with optional filtering
    """
    try:
        query = db.query(Penalty)
        
        # Apply filters
        if paid is not None:
            query = query.filter(Penalty.paid == paid)
            
        # Apply pagination
        penalties = query.offset(skip).limit(limit).all()
        
        logger.info(f"Retrieved {len(penalties)} penalties (skip={skip}, limit={limit}, paid={paid})")
        return penalties
        
    except Exception as e:
        logger.error(f"Error retrieving penalties: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Failed to retrieve penalties: {str(e)}")

@router.get("/user/{user_id}", response_model=List[PenaltyResponse])
@rate_limit()
async def get_user_penalties(
    request: Request,
    user_id: str = Path(..., description="User ID"),
    paid: Optional[bool] = Query(None, description="Filter by paid status"),
    db: Session = Depends(get_db)
):
    """
    Get all penalties for a specific user
    """
    try:
        # Verify user exists
        user = UserUtils.get_user_by_id(db, user_id=user_id)
        if not user:
            logger.warning(f"Attempt to get penalties for non-existent user: {user_id}")
            raise HTTPException(status_code=404, detail="User not found")
            
        # Get penalties for user
        query = db.query(Penalty).filter(Penalty.user_id == user_id)
        
        # Apply paid filter if provided
        if paid is not None:
            query = query.filter(Penalty.paid == paid)
            
        penalties = query.all()
        
        logger.info(f"Retrieved {len(penalties)} penalties for user {user_id}")
        return penalties
        
    except ResourceNotFoundException:
        raise HTTPException(status_code=404, detail="User not found")
    except Exception as e:
        logger.error(f"Error retrieving user penalties: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Failed to retrieve penalties: {str(e)}")

@router.get("/{penalty_id}", response_model=PenaltyResponse)
@rate_limit()
async def get_penalty(
    request: Request,
    penalty_id: str = Path(..., description="Penalty ID"),
    db: Session = Depends(get_db)
):
    """
    Get a specific penalty by ID
    """
    try:
        penalty = db.query(Penalty).filter(Penalty.penalty_id == penalty_id).first()
        if not penalty:
            logger.warning(f"Penalty not found: {penalty_id}")
            raise HTTPException(status_code=404, detail="Penalty not found")
            
        logger.info(f"Retrieved penalty: {penalty_id}")
        return penalty
        
    except Exception as e:
        logger.error(f"Error retrieving penalty {penalty_id}: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Failed to retrieve penalty: {str(e)}")

@router.patch("/{penalty_id}", response_model=PenaltyResponse)
@rate_limit()
async def update_penalty(
    request: Request,
    penalty_id: str = Path(..., description="Penalty ID"),
    penalty_update: PenaltyUpdate = ...,
    db: Session = Depends(get_db)
):
    """
    Update a penalty
    """
    try:
        penalty = db.query(Penalty).filter(Penalty.penalty_id == penalty_id).first()
        if not penalty:
            logger.warning(f"Attempt to update non-existent penalty: {penalty_id}")
            raise HTTPException(status_code=404, detail="Penalty not found")
        
        # Update fields if provided
        if penalty_update.amount is not None:
            penalty.amount = penalty_update.amount
        if penalty_update.reason is not None:
            penalty.reason = penalty_update.reason
        if penalty_update.date is not None:
            penalty.date = penalty_update.date
        if penalty_update.paid is not None:
            penalty.paid = penalty_update.paid
            if penalty_update.paid:
                penalty.paid_at = datetime.utcnow()
            else:
                penalty.paid_at = None
        
        db.commit()
        db.refresh(penalty)
        
        logger.info(f"Updated penalty: {penalty_id}")
        return penalty
        
    except Exception as e:
        db.rollback()
        logger.error(f"Error updating penalty {penalty_id}: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Failed to update penalty: {str(e)}")

@router.patch("/{penalty_id}/pay", response_model=PenaltyResponse)
@rate_limit()
async def mark_penalty_paid(
    request: Request,
    penalty_id: str = Path(..., description="Penalty ID"),
    db: Session = Depends(get_db)
):
    """
    Mark a penalty as paid
    """
    try:
        penalty = db.query(Penalty).filter(Penalty.penalty_id == penalty_id).first()
        if not penalty:
            logger.warning(f"Attempt to mark non-existent penalty as paid: {penalty_id}")
            raise HTTPException(status_code=404, detail="Penalty not found")
            
        # Mark as paid
        penalty.mark_as_paid()
        
        db.commit()
        db.refresh(penalty)
        
        logger.info(f"Marked penalty as paid: {penalty_id}")
        return penalty
        
    except Exception as e:
        db.rollback()
        logger.error(f"Error marking penalty as paid {penalty_id}: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Failed to mark penalty as paid: {str(e)}")

@router.delete("/{penalty_id}", status_code=204)
@rate_limit()
async def delete_penalty(
    request: Request,
    penalty_id: str = Path(..., description="Penalty ID"),
    db: Session = Depends(get_db)
):
    """
    Delete a penalty
    """
    try:
        penalty = db.query(Penalty).filter(Penalty.penalty_id == penalty_id).first()
        if not penalty:
            logger.warning(f"Attempt to delete non-existent penalty: {penalty_id}")
            raise HTTPException(status_code=404, detail="Penalty not found")
            
        db.delete(penalty)
        db.commit()
        
        logger.info(f"Deleted penalty: {penalty_id}")
        
    except Exception as e:
        db.rollback()
        logger.error(f"Error deleting penalty {penalty_id}: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Failed to delete penalty: {str(e)}")
