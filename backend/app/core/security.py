"""
Security Module - Authentication & Authorization
จัดการ JWT Token, Password Hashing และ RBAC
"""

from datetime import datetime, timedelta
from typing import Any

from jose import JWTError, jwt
from passlib.context import CryptContext

from app.core.config import settings

# ============================================================================
# Password Hashing
# ============================================================================

# Context สำหรับ Bcrypt Hashing
pwd_context = CryptContext(
    schemes=["bcrypt"],
    deprecated="auto",
    bcrypt__rounds=settings.BCRYPT_ROUNDS,
)


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """
    ตรวจสอบ Password ที่ยังไม่ Hash กับ Hashed Password
    
    Args:
        plain_password: Password ที่ผู้ใช้กรอก
        hashed_password: Password ที่เก็บในฐานข้อมูล (Hashed)
    
    Returns:
        True ถ้า Password ถูกต้อง, False ถ้าไม่ถูกต้อง
    """
    return pwd_context.verify(plain_password, hashed_password)


def get_password_hash(password: str) -> str:
    """
    Hash Password ด้วย Bcrypt
    
    Args:
        password: Plain text password
    
    Returns:
        Hashed password
    """
    return pwd_context.hash(password)


# ============================================================================
# JWT Token Management
# ============================================================================


def create_access_token(
    subject: str | int,
    expires_delta: timedelta | None = None,
    additional_claims: dict[str, Any] | None = None,
) -> str:
    """
    สร้าง JWT Access Token
    
    Args:
        subject: User ID หรือ Username (จะเก็บใน 'sub' claim)
        expires_delta: อายุของ Token (ถ้าไม่ระบุใช้ค่า default จาก settings)
        additional_claims: Claims เพิ่มเติม เช่น role, permissions
    
    Returns:
        JWT Token string
    """
    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)

    to_encode = {
        "exp": expire,
        "iat": datetime.utcnow(),
        "sub": str(subject),
        "type": "access",
    }

    # เพิ่ม Claims เพิ่มเติม (เช่น role, permissions)
    if additional_claims:
        to_encode.update(additional_claims)

    encoded_jwt = jwt.encode(to_encode, settings.SECRET_KEY, algorithm=settings.ALGORITHM)
    return encoded_jwt


def create_refresh_token(subject: str | int) -> str:
    """
    สร้าง JWT Refresh Token (อายุยาวกว่า Access Token)
    
    Args:
        subject: User ID
    
    Returns:
        JWT Refresh Token string
    """
    expire = datetime.utcnow() + timedelta(days=settings.REFRESH_TOKEN_EXPIRE_DAYS)

    to_encode = {
        "exp": expire,
        "iat": datetime.utcnow(),
        "sub": str(subject),
        "type": "refresh",
    }

    encoded_jwt = jwt.encode(to_encode, settings.SECRET_KEY, algorithm=settings.ALGORITHM)
    return encoded_jwt


def decode_token(token: str) -> dict[str, Any]:
    """
    Decode และตรวจสอบ JWT Token
    
    Args:
        token: JWT Token string
    
    Returns:
        Payload dictionary จาก Token
    
    Raises:
        JWTError: ถ้า Token ไม่ถูกต้องหรือหมดอายุ
    """
    try:
        payload = jwt.decode(token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM])
        return payload
    except JWTError as e:
        raise JWTError(f"Token validation failed: {str(e)}")


def verify_token_type(token_payload: dict[str, Any], expected_type: str = "access") -> bool:
    """
    ตรวจสอบประเภทของ Token (access หรือ refresh)
    
    Args:
        token_payload: Payload ที่ decode จาก Token
        expected_type: ประเภทที่คาดหวัง ('access' หรือ 'refresh')
    
    Returns:
        True ถ้าประเภทถูกต้อง
    """
    token_type = token_payload.get("type")
    return token_type == expected_type


# ============================================================================
# Role-Based Access Control (RBAC) Helpers
# ============================================================================


def check_permission(user_role: str, required_roles: list[str]) -> bool:
    """
    ตรวจสอบว่า User มี Role ที่อนุญาตหรือไม่
    
    Args:
        user_role: Role ของ User
        required_roles: List ของ Roles ที่อนุญาต
    
    Returns:
        True ถ้า User มีสิทธิ์เข้าถึง
    """
    return user_role in required_roles


# Role Hierarchy (Admin มีสิทธิ์มากที่สุด)
ROLE_HIERARCHY = {
    "admin": 3,
    "staff": 2,
    "student": 1,
}


def has_higher_role(user_role: str, minimum_role: str) -> bool:
    """
    ตรวจสอบว่า User มี Role ที่สูงกว่าหรือเท่ากับที่กำหนด
    
    Args:
        user_role: Role ของ User
        minimum_role: Role ขั้นต่ำที่ต้องการ
    
    Returns:
        True ถ้า User มีสิทธิ์เพียงพอ
    """
    user_level = ROLE_HIERARCHY.get(user_role, 0)
    required_level = ROLE_HIERARCHY.get(minimum_role, 0)
    return user_level >= required_level
