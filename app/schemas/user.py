"""Pydantic schemas for user profiles."""

from datetime import datetime, date
from typing import Optional
from pydantic import BaseModel, ConfigDict, Field
from app.models.user import GenderEnum, UserGroupEnum


class UserProfileCreate(BaseModel):
    """User profile creation schema."""

    first_name: Optional[str] = Field(None, max_length=100)
    last_name: Optional[str] = Field(None, max_length=100)
    gender: Optional[GenderEnum] = None
    date_of_birth: Optional[date] = None
    info: Optional[str] = None


class UserProfileUpdate(BaseModel):
    """User profile update schema."""

    first_name: Optional[str] = Field(None, max_length=100)
    last_name: Optional[str] = Field(None, max_length=100)
    gender: Optional[GenderEnum] = None
    date_of_birth: Optional[date] = None
    info: Optional[str] = None


class UserProfileResponse(BaseModel):
    """User profile response schema."""

    id: int
    user_id: int
    first_name: Optional[str]
    last_name: Optional[str]
    avatar: Optional[str]
    gender: Optional[GenderEnum]
    date_of_birth: Optional[date]
    info: Optional[str]

    model_config = ConfigDict(from_attributes=True)


class UserFullResponse(BaseModel):
    """Full user info with profile."""

    id: int
    email: str
    is_active: bool
    created_at: datetime
    group_name: str
    profile: Optional[UserProfileResponse]

    model_config = ConfigDict(from_attributes=True)


class UserAdminUpdate(BaseModel):
    """Administrator input for account status and role."""

    group: Optional[UserGroupEnum] = None
    is_active: Optional[bool] = None


class UserAdminResponse(BaseModel):
    """Administrator view of a user account."""

    id: int
    email: str
    is_active: bool
    group_name: str
