"""User models for authentication and authorization."""

import enum
from datetime import UTC, datetime
from sqlalchemy import Column, Integer, String, Boolean, DateTime, ForeignKey, Enum as SQLEnum
from sqlalchemy.orm import relationship
from app.db.session import Base


class UserGroupEnum(str, enum.Enum):
    """User group types."""

    USER = "user"
    MODERATOR = "moderator"
    ADMIN = "admin"


class GenderEnum(str, enum.Enum):
    """Gender types."""

    MAN = "man"
    WOMAN = "woman"


class UserGroup(Base):
    """User groups table."""

    __tablename__ = "user_groups"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(50), unique=True, nullable=False)

    users = relationship("User", back_populates="group")


class User(Base):
    """Users table."""

    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    email = Column(String(255), unique=True, nullable=False, index=True)
    hashed_password = Column(String(255), nullable=False)
    is_active = Column(Boolean, default=False, nullable=False)
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(UTC), nullable=False)
    updated_at = Column(
        DateTime(timezone=True), default=lambda: datetime.now(UTC), onupdate=lambda: datetime.now(UTC), nullable=False
    )
    group_id = Column(Integer, ForeignKey("user_groups.id"), nullable=False)

    group = relationship("UserGroup", back_populates="users")
    profile = relationship("UserProfile", back_populates="user", uselist=False, cascade="all, delete-orphan")
    activation_token = relationship(
        "ActivationToken", back_populates="user", uselist=False, cascade="all, delete-orphan"
    )
    password_reset_token = relationship(
        "PasswordResetToken", back_populates="user", uselist=False, cascade="all, delete-orphan"
    )
    refresh_tokens = relationship("RefreshToken", back_populates="user", cascade="all, delete-orphan")


class UserProfile(Base):
    """User profiles table."""

    __tablename__ = "user_profiles"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), unique=True, nullable=False)
    first_name = Column(String(100), nullable=True)
    last_name = Column(String(100), nullable=True)
    avatar = Column(String(255), nullable=True)
    gender = Column(SQLEnum(GenderEnum), nullable=True)
    date_of_birth = Column(DateTime(timezone=True), nullable=True)
    info = Column(String, nullable=True)

    user = relationship("User", back_populates="profile")


class ActivationToken(Base):
    """Activation tokens table."""

    __tablename__ = "activation_tokens"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), unique=True, nullable=False)
    token = Column(String(255), unique=True, nullable=False, index=True)
    expires_at = Column(DateTime(timezone=True), nullable=False)

    user = relationship("User", back_populates="activation_token")


class PasswordResetToken(Base):
    """Password reset tokens table."""

    __tablename__ = "password_reset_tokens"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), unique=True, nullable=False)
    token = Column(String(255), unique=True, nullable=False, index=True)
    expires_at = Column(DateTime(timezone=True), nullable=False)

    user = relationship("User", back_populates="password_reset_token")


class RefreshToken(Base):
    """Refresh tokens table."""

    __tablename__ = "refresh_tokens"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    token = Column(String(255), unique=True, nullable=False, index=True)
    expires_at = Column(DateTime(timezone=True), nullable=False)

    user = relationship("User", back_populates="refresh_tokens")
