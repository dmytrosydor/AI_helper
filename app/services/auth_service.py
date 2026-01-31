from sqlalchemy.orm import Session

from app.models.user import User

from app.schemas.user import UserCreate
from app.core.security import hash_password, verify_password, create_access_token


def register_user(db: Session, user_data: UserCreate) -> User:
    user = User(
        email=user_data.email,
        hashed_password=hash_password(user_data.password),
        full_name=user_data.username,
        is_active=True,
        is_superuser=False,
    )

    db.add(user)
    db.commit()
    db.refresh(user)
    return user


def authenticate_user(db: Session, username: str, password: str) -> str:
    user = db.query(User).filter(User.full_name == username).first()
    if not user:
        return None

    if not verify_password(password, user.hashed_password):
        return None

    return create_access_token({"sub":str(user.id)})