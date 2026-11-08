"""User profile API endpoints."""

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile, status
from PIL import Image, UnidentifiedImageError
from starlette.concurrency import run_in_threadpool
from io import BytesIO
from sqlalchemy.ext.asyncio import AsyncSession
from app.db.session import get_db
from app.schemas.user import (
    UserAdminResponse,
    UserAdminUpdate,
    UserProfileCreate,
    UserProfileUpdate,
    UserProfileResponse,
    UserFullResponse,
)
from app.services import user_service
from app.api.dependencies import get_current_active_user, get_current_admin
from app.models.user import User
from app.services.auth_service import get_user_by_id
from app.services.storage_service import upload_avatar

router = APIRouter(prefix="/users", tags=["Users"])


def _admin_response(user: User) -> dict:
    """Serialize user data for administrator endpoints."""
    return {"id": user.id, "email": user.email, "is_active": user.is_active, "group_name": user.group.name}


@router.get("/me", response_model=UserFullResponse)
async def get_my_profile(current_user: User = Depends(get_current_active_user), db: AsyncSession = Depends(get_db)):
    """Get current user profile."""
    profile = await user_service.get_user_profile(db, current_user.id)
    return {
        "id": current_user.id,
        "email": current_user.email,
        "is_active": current_user.is_active,
        "created_at": current_user.created_at,
        "group_name": current_user.group.name,
        "profile": profile,
    }


@router.post("/me/profile", response_model=UserProfileResponse, status_code=status.HTTP_201_CREATED)
async def create_my_profile(
    data: UserProfileCreate, current_user: User = Depends(get_current_active_user), db: AsyncSession = Depends(get_db)
):
    """Create user profile."""
    existing_profile = await user_service.get_user_profile(db, current_user.id)
    if existing_profile:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Profile already exists")

    profile = await user_service.create_user_profile(db, current_user.id, data)
    return profile


@router.put("/me/profile", response_model=UserProfileResponse)
async def update_my_profile(
    data: UserProfileUpdate, current_user: User = Depends(get_current_active_user), db: AsyncSession = Depends(get_db)
):
    """Update user profile."""
    profile = await user_service.get_or_create_profile(db, current_user.id)
    updated_profile = await user_service.update_user_profile(db, profile, data)
    return updated_profile


@router.post("/me/avatar", response_model=UserProfileResponse)
async def upload_my_avatar(
    avatar: UploadFile = File(...),
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
):
    """Upload a JPEG, PNG, or WEBP avatar to MinIO."""
    content = await avatar.read()
    if len(content) > 5 * 1024 * 1024:
        raise HTTPException(status_code=400, detail="Avatar must not exceed 5 MB")

    try:
        image = Image.open(BytesIO(content))
        image.verify()
    except (UnidentifiedImageError, OSError):
        raise HTTPException(status_code=400, detail="Avatar must be a valid JPEG, PNG, or WEBP image")
    image_format = image.format
    content_type = {"JPEG": "image/jpeg", "PNG": "image/png", "WEBP": "image/webp"}.get(image_format or "")
    if not content_type:
        raise HTTPException(status_code=400, detail="Avatar must be JPEG, PNG, or WEBP")

    profile = await user_service.get_or_create_profile(db, current_user.id)
    try:
        profile.avatar = await run_in_threadpool(upload_avatar, content, content_type)
    except Exception as error:
        raise HTTPException(status_code=503, detail="Avatar storage is unavailable") from error
    await db.commit()
    await db.refresh(profile)
    return profile


@router.get("", response_model=list[UserAdminResponse])
async def list_users(db: AsyncSession = Depends(get_db), _=Depends(get_current_admin)):
    """List user accounts. Administrator access is required."""
    return [_admin_response(user) for user in await user_service.list_users(db)]


@router.patch("/{user_id}", response_model=UserAdminResponse)
async def update_user(
    user_id: int,
    data: UserAdminUpdate,
    db: AsyncSession = Depends(get_db),
    _=Depends(get_current_admin),
):
    """Change a user's group or manually activate the account."""
    user = await get_user_by_id(db, user_id)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    try:
        user = await user_service.update_user_by_admin(
            db, user, data.group.value if data.group else None, data.is_active
        )
    except ValueError as error:
        raise HTTPException(status_code=400, detail=str(error)) from error
    return _admin_response(user)
