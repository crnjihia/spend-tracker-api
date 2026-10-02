"""Authentication request and response Pydantic schemas."""

from datetime import datetime
from typing import Optional

from pydantic import BaseModel, ConfigDict, EmailStr, Field


class RegisterRequest(BaseModel):
    """Payload for user registration."""

    email: EmailStr = Field(
        ..., description="User's unique email address", examples=["alice@example.com"]
    )
    password: str = Field(
        ...,
        min_length=8,
        description="Password (at least 8 characters)",
        examples=["SecureP@ss123"],
    )
    full_name: Optional[str] = Field(
        None, description="Full name of user", examples=["Alice Wanjiku"]
    )


class RegisterResponse(BaseModel):
    """Response returned upon successful registration."""

    id: str
    email: EmailStr
    full_name: Optional[str] = None
    role: str
    is_active: bool
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class LoginRequest(BaseModel):
    """Payload for user login."""

    email: EmailStr = Field(
        ..., description="Registered email address", examples=["alice@example.com"]
    )
    password: str = Field(..., description="User password", examples=["SecureP@ss123"])


class TokenResponse(BaseModel):
    """JWT token pair returned upon successful authentication or rotation."""

    access_token: str = Field(..., description="Short-lived JWT access token (15 mins)")
    refresh_token: str = Field(..., description="Long-lived JWT refresh token (7 days)")
    token_type: str = Field(default="bearer", description="Token authentication type")


class RefreshRequest(BaseModel):
    """Payload for refreshing an access token using a refresh token."""

    refresh_token: str = Field(..., description="Current valid refresh token")


class LogoutRequest(BaseModel):
    """Payload for logging out and revoking a refresh token."""

    refresh_token: str = Field(..., description="Refresh token to revoke")
