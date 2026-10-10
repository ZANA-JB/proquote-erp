from datetime import datetime, timedelta, timezone
from typing import Any, Dict, Optional

from jose import JWTError, jwt
"""Centralise le hachage des mots de passe et les jetons JWT."""

from passlib.context import CryptContext

from app.core.config import settings

pwd_context = CryptContext(
    schemes=["pbkdf2_sha256"],
    pbkdf2_sha256__rounds=600_000,
    deprecated="auto",
)


def get_password_hash(password: str) -> str:
    return pwd_context.hash(password)


def verify_password(plain_password: str, hashed_password: str) -> bool:
    return pwd_context.verify(plain_password, hashed_password)


def verify_password_and_update(plain_password: str, hashed_password: str) -> tuple[bool, str | None]:
    return pwd_context.verify_and_update(plain_password, hashed_password)


def create_access_token(data: Dict[str, Any], expires_delta: Optional[timedelta] = None) -> str:
    to_encode = data.copy()
    expire = datetime.now(timezone.utc) + (expires_delta or timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES))
    to_encode.update({"exp": expire})
    return jwt.encode(to_encode, settings.SECRET_KEY, algorithm=settings.ALGORITHM)


def decode_access_token(token: str) -> Dict[str, Any]:
    try:
        payload = jwt.decode(token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM])
    except JWTError as exc:
        raise exc
    user_id = payload.get("sub")
    role = payload.get("role")
    token_version = payload.get("ver", 0)
    if user_id is None or role is None or type(token_version) is not int:
        raise JWTError("Invalid token payload")
    return {"sub": user_id, "role": role, "ver": token_version}
