# backend/app/api/v1/endpoints/users.py

from fastapi import APIRouter, Depends
from app.schemas.user import User
from app.api import deps

router = APIRouter()

@router.get("/me", response_model=User)
def read_users_me(current_user: User = Depends(deps.get_current_user)):
    return current_user