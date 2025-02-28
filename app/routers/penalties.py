from fastapi import APIRouter, HTTPException
from ..database import crud
from ..database.schemas import Penalty
from typing import List

router = APIRouter(
    prefix="/penalties",
    tags=["Penalties"]
)

@router.get("/{user_id}", response_model=List[Penalty])
def read_unpaid_penalties(user_id: int):
    penalties = crud.get_penalties(user_id)
    if not penalties:
        raise HTTPException(status_code=404, detail="No unpaid penalties found.")
    return penalties

@router.put("/update/{user_id}")
def update_user_penalties(user_id: int):
    user = crud.get_user(user_id)
    if not user:
        raise HTTPException(status_code=404, detail="User not found.")
    from datetime import datetime
    current_date = datetime.now().strftime('%Y-%m-%d')
    crud.update_penalties(user_id, current_date)
    return {"message": "Penalties updated successfully."}
