from datetime import datetime, timedelta
from jose import jwt
from passlib.context import CryptContext
from pyasn1_modules.rfc3125 import AlgorithmConstraints

from app.core.config import settings

pwd_cotext = CryptContext(schemes=["bcrypt"], deprecated="auto")

ALGORITHMS = ["HS256"]


def hash_password(password):
    return pwd_cotext.hash(password)


def verify_password(plain_password, hashed_password):
    return pwd_cotext.verify(plain_password, hashed_password)


def create_access_token(data: dict, expires_minutes: int = 60):
    to_encode = data.copy()
    expire = datetime.utcnow() + timedelta(minutes=expires_minutes)
    to_encode.update({"exp": expire})

    return jwt.encode(
        to_encode,
        settings.SECRET_KEY,
        algorithm="HS256"
    )
