"""Security utilities for password hashing, token generation, and verification."""

import hashlib
import uuid
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, Optional

import bcrypt
from jose import jwt

from app.core.config import settings


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Verify that a plain text password matches its hashed representation.

    Args:
        plain_password: The unhashed password string.
        hashed_password: The hashed password string stored in database.

    Returns:
        bool: True if passwords match, False otherwise.
    """
    try:
        return bcrypt.checkpw(
            plain_password.encode("utf-8"),
            hashed_password.encode("utf-8"),
        )
    except Exception:
        return False


def get_password_hash(password: str) -> str:
    """Generate a bcrypt hash of the provided password.

    Args:
        password: Plain text password string.

    Returns:
        str: Bcrypt hashed password.
    """
    salt = bcrypt.gensalt()
    return bcrypt.hashpw(password.encode("utf-8"), salt).decode("utf-8")


def hash_token(raw_token: str) -> str:
    """Generate a deterministic SHA-256 hash of a raw token for database storage and indexing.

    Args:
        raw_token: The raw JWT or string token.

    Returns:
        str: Hexadecimal SHA-256 digest string.
    """
    return hashlib.sha256(raw_token.encode("utf-8")).hexdigest()


def create_access_token(
    subject: str,
    expires_delta: Optional[timedelta] = None,
    extra_claims: Optional[Dict[str, Any]] = None,
) -> str:
    """Generate a signed JWT access token.

    Args:
        subject: The primary identifier (usually user UUID string).
        expires_delta: Optional timedelta for token expiration. Defaults to settings.
        extra_claims: Optional dictionary of additional claims.

    Returns:
        str: Encoded JWT access token.
    """
    now = datetime.now(timezone.utc)
    expire = now + (expires_delta or timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES))
    to_encode: Dict[str, Any] = {
        "sub": subject,
        "jti": uuid.uuid4().hex,
        "iat": int(now.timestamp()),
        "exp": int(expire.timestamp()),
        "type": "access",
    }
    if extra_claims:
        to_encode.update(extra_claims)

    return jwt.encode(
        to_encode,
        settings.JWT_SECRET_KEY,
        algorithm=settings.JWT_ALGORITHM,
    )


def create_refresh_token(
    subject: str,
    expires_delta: Optional[timedelta] = None,
) -> str:
    """Generate a signed JWT refresh token with unique jti claim.

    Args:
        subject: The primary identifier (usually user UUID string).
        expires_delta: Optional timedelta for token expiration. Defaults to settings.

    Returns:
        str: Encoded JWT refresh token.
    """
    now = datetime.now(timezone.utc)
    expire = now + (expires_delta or timedelta(days=settings.REFRESH_TOKEN_EXPIRE_DAYS))
    to_encode: Dict[str, Any] = {
        "sub": subject,
        "jti": uuid.uuid4().hex,
        "iat": int(now.timestamp()),
        "exp": int(expire.timestamp()),
        "type": "refresh",
    }
    return jwt.encode(
        to_encode,
        settings.JWT_SECRET_KEY,
        algorithm=settings.JWT_ALGORITHM,
    )
