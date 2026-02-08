from fastapi import APIRouter, Depends, HTTPException, status, Response, Cookie
from sqlalchemy.orm import Session
from fastapi.security import OAuth2PasswordRequestForm
from jose import jwt, JWTError

from app.schemas.user import UserCreate, UserResponse, Token
from app.services.auth_service import register_user
from app.core.db import get_db
from app.core.security import create_access_token, create_refresh_token, verify_password
from app.core.config import settings
from app.models.user import User

router = APIRouter(prefix="/auth", tags=["Auth"])


@router.post("/register", response_model=UserResponse)
def register(user_data: UserCreate, db: Session = Depends(get_db)):
    # TODO: add email verification
    return register_user(db, user_data)


@router.post("/login", response_model=Token)
def login(
        response: Response,
        form_data: OAuth2PasswordRequestForm = Depends(),
        db: Session = Depends(get_db)
):
    user = db.query(User).filter(User.email == form_data.username).first()

    if not user or not verify_password(form_data.password, user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect email or password",
            headers={"WWW-Authenticate": "Bearer"}
        )

    access_token = create_access_token(data={"sub": str(user.id)})
    refresh_token = create_refresh_token(data={"sub": str(user.id)})


    response.set_cookie(
        key="refresh_token",
        value=refresh_token,
        httponly=True,   # 🛡️ JS не має доступу
        secure=False,    # ⚠️ Зміни на True, коли підключиш HTTPS (на проді)
        samesite="lax",  # Захист від CSRF
        max_age=7 * 24 * 60 * 60  # 7 днів
    )

    return {
        "access_token": access_token,
        "token_type": "bearer",
    }


@router.post("/refresh", response_model=Token)
def refresh_token(
        response: Response,
        refresh_token: str | None = Cookie(None),  # FastAPI сам дістане з кук
        db: Session = Depends(get_db)
):
    """
    Приймає refresh_token з кук і оновлює пару (Access + Cookie Refresh).
    """
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )

    if not refresh_token:
        raise credentials_exception

    try:

        payload = jwt.decode(refresh_token, settings.SECRET_KEY, algorithms=["HS256"])
        user_id: str = payload.get("sub")
        token_type: str = payload.get("type")

        if user_id is None or token_type != "refresh":
            raise credentials_exception


        user = db.query(User).filter(User.id == int(user_id)).first()
        if user is None:
            raise credentials_exception


        new_access_token = create_access_token(data={"sub": str(user.id)})
        new_refresh_token = create_refresh_token(data={"sub": str(user.id)})


        response.set_cookie(
            key="refresh_token",
            value=new_refresh_token,
            httponly=True,
            secure=False,
            samesite="lax",
            max_age=7 * 24 * 60 * 60
        )


        return {
            "access_token": new_access_token,
            "token_type": "bearer",
        }

    except JWTError:
        raise credentials_exception


@router.post("/logout")
def logout(response: Response):
    """
    Видаляє куку з refresh token.
    """
    response.delete_cookie("refresh_token")
    return {"message": "Logged out successfully"}
