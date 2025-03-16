from fastapi import APIRouter, Depends, HTTPException, Query, Path, status
from sqlalchemy.orm import Session
from typing import List, Optional

from app.database import crud, schemas
from app.database.models import get_db
from app.utils.logging_config import get_logger

router = APIRouter(tags=["transactions"], prefix="/transactions")
logger = get_logger(__name__)

@router.post("/", response_model=schemas.TransactionResponse, status_code=status.HTTP_201_CREATED)
def create_transaction(
    transaction: schemas.TransactionCreate,
    db: Session = Depends(get_db)
):
    """
    Create a new transaction
    """
    # Verify user exists
    user = crud.get_user(db, user_id=transaction.user_id)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"User with ID {transaction.user_id} not found"
        )
    
    return crud.create_transaction(db=db, transaction=transaction)

@router.get("/", response_model=List[schemas.TransactionResponse])
def read_transactions(
    skip: int = Query(0, ge=0, description="Skip N transactions"),
    limit: int = Query(100, ge=1, le=100, description="Limit the number of transactions returned"),
    db: Session = Depends(get_db)
):
    """
    Get a list of transactions with pagination
    """
    # This endpoint would need to be implemented in crud.py
    # For now, we'll return an empty list
    return []

@router.get("/{transaction_id}", response_model=schemas.TransactionResponse)
def read_transaction(
    transaction_id: str = Path(..., description="The ID of the transaction to get"),
    db: Session = Depends(get_db)
):
    """
    Get detailed information about a specific transaction
    """
    # This endpoint would need to be implemented in crud.py
    raise HTTPException(
        status_code=status.HTTP_501_NOT_IMPLEMENTED,
        detail="This endpoint is not yet implemented"
    )

@router.get("/user/{user_id}", response_model=List[schemas.TransactionResponse])
def get_user_transactions(
    user_id: str = Path(..., description="The ID of the user"),
    db: Session = Depends(get_db)
):
    """
    Get all transactions for a specific user
    """
    # Verify user exists
    user = crud.get_user(db, user_id=user_id)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"User with ID {user_id} not found"
        )
    
    return crud.get_user_transactions(db, user_id=user_id)

@router.post("/pay-penalty/{penalty_id}", response_model=schemas.TransactionResponse)
def pay_penalty(
    penalty_id: str = Path(..., description="The ID of the penalty to pay"),
    db: Session = Depends(get_db)
):
    """
    Pay a specific penalty and record the transaction
    """
    # Get the penalty
    penalty = crud.get_penalty(db, penalty_id=penalty_id)
    if not penalty:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Penalty not found"
        )
    
    if penalty.paid:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Penalty is already paid"
        )
    
    # Create a transaction
    transaction = schemas.TransactionCreate(
        user_id=penalty.user_id,
        amount=penalty.amount,
        description=f"Payment for penalty: {penalty.reason or 'Unnamed penalty'}"
    )
    
    db_transaction = crud.create_transaction(db=db, transaction=transaction)
    
    # Mark the penalty as paid
    crud.mark_penalty_paid(db, penalty_id=penalty_id)
    
    return db_transaction