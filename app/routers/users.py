from fastapi import APIRouter
from ..database import crud
from ..database.schemas import User
from typing import List

router = APIRouter(
    prefix="/users",
    tags=["Users"]
)

@router.get("/", response_model=List[User])
def list_all_users():
    return crud.list_users()