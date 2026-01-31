from fastapi import APIRouter, Depends, HTTPException
from six import reraise
from sqlalchemy.orm import Session

from app.schemas.user import UserCreate, UserLogin, UserResponse, Token
from app.services.auth_service import register_user, authenticate_user
from app.core.db import get_db

router = APIRouter(prefix="/auth", tags=["Auth"])


@router.post("/register", response_model=UserResponse)
def register(user_data: UserCreate, db: Session = Depends(get_db)):
    return register_user(db, user_data)


@router.post("/login", response_model=Token)
def login(user_data: UserLogin, db: Session = Depends(get_db)):
    token = authenticate_user(db, user_data.username, user_data.password)
    if not token:
        raise HTTPException(status_code=401, detail="Incorrect email or password")

    return {
        "access_token": token
    }
