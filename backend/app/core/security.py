"""
Security - bcrypt password hashing และ JWT (HS256)
payload: sub (user id), role, type (access/refresh), iat, exp
"""

from datetime import UTC, datetime, timedelta
from typing import Any, Literal

import jwt
from passlib.context import CryptContext

from app.core.config import settings

TokenType = Literal["access", "refresh"]

pwd_context = CryptContext(
    schemes=["bcrypt"],
    deprecated="auto",
    bcrypt__rounds=settings.BCRYPT_ROUNDS,
)


class TokenError(Exception):
    pass


def get_password_hash(password: str) -> str:
    return pwd_context.hash(password)


def verify_password(plain_password: str, hashed_password: str) -> bool:
    return pwd_context.verify(plain_password, hashed_password)


def _create_token(
    subject: str | int, token_type: TokenType, expires: timedelta, **claims: Any
) -> str:
    now = datetime.now(UTC)
    payload = {"sub": str(subject), "type": token_type, "iat": now, "exp": now + expires, **claims}
    return jwt.encode(payload, settings.SECRET_KEY, algorithm=settings.ALGORITHM)


def create_access_token(subject: str | int, role: str) -> str:
    return _create_token(
        subject, "access", timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES), role=role
    )


def create_refresh_token(subject: str | int) -> str:
    return _create_token(subject, "refresh", timedelta(days=settings.REFRESH_TOKEN_EXPIRE_DAYS))


def decode_token(token: str, expected_type: TokenType) -> dict[str, Any]:
    """Decode และตรวจทั้งลายเซ็น วันหมดอายุ และ type ของ token"""
    try:
        payload = jwt.decode(
            token,
            settings.SECRET_KEY,
            algorithms=[settings.ALGORITHM],
            options={"require": ["exp", "sub", "type"]},
        )
    except jwt.PyJWTError as exc:
        raise TokenError("Invalid or expired token") from exc
    if payload.get("type") != expected_type:
        raise TokenError("Invalid token type")
    return payload
