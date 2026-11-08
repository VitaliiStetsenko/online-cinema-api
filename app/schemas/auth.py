"""Pydantic schemas for authentication."""

from datetime import datetime
import re

from pydantic import BaseModel, ConfigDict, EmailStr, Field, field_validator


def validate_password_complexity(password: str) -> str:
    """Require upper, lower, digit, and special password characters."""
    if not all(
        (
            re.search(r"[a-z]", password),
            re.search(r"[A-Z]", password),
            re.search(r"\d", password),
            re.search(r"[^A-Za-z0-9]", password),
        )
    ):
        raise ValueError("Password must include upper, lower, digit, and special character")
    return password


class UserRegister(BaseModel):
    """User registration schema."""

    email: EmailStr
    password: str = Field(min_length=8, max_length=100)

    _validate_password = field_validator("password")(validate_password_complexity)


class UserLogin(BaseModel):
    """User login schema."""

    email: EmailStr
    password: str


class TokenResponse(BaseModel):
    """Token response schema."""

    access_token: str
    refresh_token: str
    token_type: str = "bearer"


class RefreshTokenRequest(BaseModel):
    """Refresh token request schema."""

    refresh_token: str


class PasswordChange(BaseModel):
    """Password change schema."""

    old_password: str
    new_password: str = Field(min_length=8, max_length=100)

    _validate_password = field_validator("new_password")(validate_password_complexity)


class PasswordResetRequest(BaseModel):
    """Password reset request schema."""

    email: EmailStr


class PasswordReset(BaseModel):
    """Password reset schema."""

    token: str
    new_password: str = Field(min_length=8, max_length=100)

    _validate_password = field_validator("new_password")(validate_password_complexity)


class ActivationResend(BaseModel):
    """Activation token resend schema."""

    email: EmailStr


class UserResponse(BaseModel):
    """User response schema."""

    id: int
    email: str
    is_active: bool
    created_at: datetime
    group_name: str

    model_config = ConfigDict(from_attributes=True)
