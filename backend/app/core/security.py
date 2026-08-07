from datetime import datetime, timedelta, timezone

from jose import jwt
from passlib.context import CryptContext

from core.config import settings

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

ALGORITHM = "HS256"


def create_access_token(subject: str | int) -> str:
    expire = datetime.now(timezone.utc) + timedelta(
        seconds=settings.ACCESS_TOKEN_EXPIRE_SECONDS
    )
    to_encode = {"exp": expire, "sub": str(subject)}
    encoded_jwt = jwt.encode(to_encode, settings.SECRET_KEY, algorithm=ALGORITHM)
    return encoded_jwt


def verify_password(plain_password: str, hashed_password: str) -> bool:
    return pwd_context.verify(plain_password, hashed_password)


def get_password_hash(password: str) -> str:
    # El algoritmo bcrypt tiene un límite de 72 bytes. Truncamos la contraseña
    # para evitar un ValueError con contraseñas largas.
    return pwd_context.hash(password.encode("utf-8")[:72])
