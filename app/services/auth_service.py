"""Authentication service."""

import secrets
from datetime import UTC, datetime, timedelta
from typing import Optional
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload
from app.models.user import User, UserGroup, ActivationToken, PasswordResetToken, RefreshToken
from app.core.security import (
    get_password_hash,
    verify_password,
    create_access_token,
    create_refresh_token,
    decode_token,
)
from app.core.config import settings
from app.tasks.email_tasks import send_activation_email, send_password_reset_email


async def get_user_by_email(db: AsyncSession, email: str) -> Optional[User]:
    """Get user by email."""
    result = await db.execute(select(User).where(User.email == email))
    return result.scalar_one_or_none()


async def get_user_by_id(db: AsyncSession, user_id: int) -> Optional[User]:
    """Get user by id."""
    result = await db.execute(select(User).where(User.id == user_id).options(selectinload(User.group)))
    return result.scalar_one_or_none()


def _is_expired(expires_at: datetime) -> bool:
    """Compare expiry timestamps from databases that may omit UTC tzinfo."""
    if expires_at.tzinfo is None:
        expires_at = expires_at.replace(tzinfo=UTC)
    return expires_at < datetime.now(UTC)


async def create_user(db: AsyncSession, email: str, password: str) -> User:
    """Create new user with activation token."""
    # Check if user exists
    existing_user = await get_user_by_email(db, email)
    if existing_user:
        raise ValueError("User with this email already exists")

    # Get default user group
    result = await db.execute(select(UserGroup).where(UserGroup.name == "user"))
    user_group = result.scalar_one_or_none()
    if not user_group:
        raise ValueError("Default user group not found")

    # Create user
    user = User(email=email, hashed_password=get_password_hash(password), is_active=False, group_id=user_group.id)
    db.add(user)
    await db.flush()

    # Create activation token
    token = secrets.token_urlsafe(32)
    activation_token = ActivationToken(user_id=user.id, token=token, expires_at=datetime.now(UTC) + timedelta(hours=24))
    db.add(activation_token)
    await db.commit()
    await db.refresh(user)

    # Send activation email
    send_activation_email.delay(email, token)

    return user


async def activate_user(db: AsyncSession, token: str) -> bool:
    """Activate user account."""
    result = await db.execute(select(ActivationToken).where(ActivationToken.token == token))
    activation_token = result.scalar_one_or_none()

    if not activation_token:
        return False

    if _is_expired(activation_token.expires_at):
        return False

    # Activate user
    user = await get_user_by_id(db, activation_token.user_id)
    if not user:
        return False
    user.is_active = True

    # Delete token
    await db.delete(activation_token)
    await db.commit()

    return True


async def resend_activation(db: AsyncSession, email: str) -> bool:
    """Resend activation token."""
    user = await get_user_by_email(db, email)
    if not user or user.is_active:
        return False

    # Delete old token if exists
    result = await db.execute(select(ActivationToken).where(ActivationToken.user_id == user.id))
    old_token = result.scalar_one_or_none()
    if old_token:
        await db.delete(old_token)
        await db.flush()

    # Create new token
    token = secrets.token_urlsafe(32)
    activation_token = ActivationToken(user_id=user.id, token=token, expires_at=datetime.now(UTC) + timedelta(hours=24))
    db.add(activation_token)
    await db.commit()

    # Send email
    send_activation_email.delay(email, token)

    return True


async def authenticate_user(db: AsyncSession, email: str, password: str) -> Optional[User]:
    """Authenticate user."""
    user = await get_user_by_email(db, email)
    if not user:
        return None
    if not user.is_active:
        return None
    if not verify_password(password, user.hashed_password):
        return None
    return user


async def create_tokens(db: AsyncSession, user: User) -> dict:
    """Create access and refresh tokens."""
    access_token = create_access_token({"sub": str(user.id)})
    refresh_token_str = create_refresh_token({"sub": str(user.id)})

    # Save refresh token to DB
    refresh_token = RefreshToken(
        user_id=user.id,
        token=refresh_token_str,
        expires_at=datetime.now(UTC) + timedelta(days=settings.refresh_token_expire_days),
    )
    db.add(refresh_token)
    await db.commit()

    return {"access_token": access_token, "refresh_token": refresh_token_str, "token_type": "bearer"}


async def refresh_access_token(db: AsyncSession, refresh_token_str: str) -> Optional[dict]:
    """Refresh access token."""
    # Verify token
    payload = decode_token(refresh_token_str)
    if not payload or payload.get("type") != "refresh":
        return None

    # Check if token exists in DB
    result = await db.execute(select(RefreshToken).where(RefreshToken.token == refresh_token_str))
    refresh_token = result.scalar_one_or_none()

    if not refresh_token or _is_expired(refresh_token.expires_at):
        return None

    # Create new access token
    subject = payload.get("sub")
    if not isinstance(subject, str):
        return None
    user = await get_user_by_id(db, int(subject))
    if not user or not user.is_active:
        return None

    await db.delete(refresh_token)
    return await create_tokens(db, user)


async def logout_user(db: AsyncSession, refresh_token_str: str) -> bool:
    """Logout user by deleting refresh token."""
    result = await db.execute(select(RefreshToken).where(RefreshToken.token == refresh_token_str))
    refresh_token = result.scalar_one_or_none()

    if refresh_token:
        await db.delete(refresh_token)
        await db.commit()
        return True
    return False


async def change_password(db: AsyncSession, user: User, old_password: str, new_password: str) -> bool:
    """Change user password."""
    if not verify_password(old_password, user.hashed_password):
        return False

    user.hashed_password = get_password_hash(new_password)
    user.updated_at = datetime.now(UTC)
    await db.commit()

    return True


async def request_password_reset(db: AsyncSession, email: str) -> bool:
    """Request password reset."""
    user = await get_user_by_email(db, email)
    if not user or not user.is_active:
        return False

    # Delete old token if exists
    result = await db.execute(select(PasswordResetToken).where(PasswordResetToken.user_id == user.id))
    old_token = result.scalar_one_or_none()
    if old_token:
        await db.delete(old_token)
        await db.flush()

    # Create new token
    token = secrets.token_urlsafe(32)
    reset_token = PasswordResetToken(user_id=user.id, token=token, expires_at=datetime.now(UTC) + timedelta(hours=1))
    db.add(reset_token)
    await db.commit()

    # Send email
    send_password_reset_email.delay(email, token)

    return True


async def reset_password(db: AsyncSession, token: str, new_password: str) -> bool:
    """Reset password using token."""
    result = await db.execute(select(PasswordResetToken).where(PasswordResetToken.token == token))
    reset_token = result.scalar_one_or_none()

    if not reset_token or _is_expired(reset_token.expires_at):
        return False

    # Reset password
    user = await get_user_by_id(db, reset_token.user_id)
    if not user:
        return False
    user.hashed_password = get_password_hash(new_password)
    user.updated_at = datetime.now(UTC)

    # Delete token
    await db.delete(reset_token)
    await db.commit()

    return True
