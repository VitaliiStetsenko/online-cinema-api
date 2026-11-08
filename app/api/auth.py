"""Authentication API endpoints."""

from fastapi import APIRouter, Depends, HTTPException, Request, status
from sqlalchemy.ext.asyncio import AsyncSession
from app.db.session import get_db
from app.schemas.auth import (
    UserRegister,
    UserLogin,
    TokenResponse,
    RefreshTokenRequest,
    PasswordChange,
    PasswordResetRequest,
    PasswordReset,
    ActivationResend,
)
from app.services import auth_service
from app.api.dependencies import get_current_user
from app.models.user import User
from app.core.config import settings
from app.core.rate_limit import limiter

router = APIRouter(prefix="/auth", tags=["Authentication"])


@router.post("/register", status_code=status.HTTP_201_CREATED)
@limiter.limit(settings.auth_rate_limit)
async def register(request: Request, data: UserRegister, db: AsyncSession = Depends(get_db)):
    """Register new user. Sends activation email."""
    try:
        user = await auth_service.create_user(db, data.email, data.password)
        return {"message": "User created successfully. Check your email for activation link.", "email": user.email}
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))


@router.post("/activate/{token}")
async def activate(token: str, db: AsyncSession = Depends(get_db)):
    """Activate user account with token."""
    success = await auth_service.activate_user(db, token)
    if not success:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid or expired activation token")
    return {"message": "Account activated successfully"}


@router.post("/resend-activation")
@limiter.limit(settings.auth_rate_limit)
async def resend_activation(request: Request, data: ActivationResend, db: AsyncSession = Depends(get_db)):
    """Resend activation email."""
    success = await auth_service.resend_activation(db, data.email)
    if not success:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="User not found or already activated")
    return {"message": "Activation email sent"}


@router.post("/login", response_model=TokenResponse)
@limiter.limit(settings.auth_rate_limit)
async def login(request: Request, data: UserLogin, db: AsyncSession = Depends(get_db)):
    """Login user and return JWT tokens."""
    user = await auth_service.authenticate_user(db, data.email, data.password)
    if not user:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Incorrect email or password")

    tokens = await auth_service.create_tokens(db, user)
    return tokens


@router.post("/refresh", response_model=TokenResponse)
async def refresh_token(data: RefreshTokenRequest, db: AsyncSession = Depends(get_db)):
    """Refresh access token using refresh token."""
    result = await auth_service.refresh_access_token(db, data.refresh_token)
    if not result:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid or expired refresh token")
    return result


@router.post("/logout")
async def logout(data: RefreshTokenRequest, db: AsyncSession = Depends(get_db)):
    """Logout user by deleting refresh token."""
    await auth_service.logout_user(db, data.refresh_token)
    return {"message": "Logged out successfully"}


@router.post("/change-password")
async def change_password(
    data: PasswordChange, current_user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)
):
    """Change user password."""
    success = await auth_service.change_password(db, current_user, data.old_password, data.new_password)
    if not success:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Incorrect old password")
    return {"message": "Password changed successfully"}


@router.post("/request-password-reset")
@limiter.limit(settings.auth_rate_limit)
async def request_password_reset(request: Request, data: PasswordResetRequest, db: AsyncSession = Depends(get_db)):
    """Request password reset. Sends email with reset token."""
    await auth_service.request_password_reset(db, data.email)
    return {"message": "If email exists, password reset link has been sent"}


@router.post("/reset-password")
async def reset_password(data: PasswordReset, db: AsyncSession = Depends(get_db)):
    """Reset password using token."""
    success = await auth_service.reset_password(db, data.token, data.new_password)
    if not success:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid or expired reset token")
    return {"message": "Password reset successfully"}
