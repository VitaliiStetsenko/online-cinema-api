"""Pytest configuration and fixtures."""

import os
from typing import AsyncGenerator

import pytest
from httpx import AsyncClient, ASGITransport
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine, async_sessionmaker

os.environ.setdefault("DATABASE_URL", "sqlite+aiosqlite:///:memory:")
os.environ.setdefault("SECRET_KEY", "test-secret-key")
os.environ.setdefault("SMTP_HOST", "localhost")
os.environ.setdefault("SMTP_PORT", "1025")
os.environ.setdefault("SMTP_USER", "test")
os.environ.setdefault("SMTP_PASSWORD", "test")
os.environ.setdefault("EMAIL_FROM", "test@example.com")
os.environ.setdefault("REDIS_URL", "redis://localhost:6379/0")
os.environ.setdefault("CELERY_BROKER_URL", "redis://localhost:6379/1")
os.environ.setdefault("CELERY_RESULT_BACKEND", "redis://localhost:6379/2")
os.environ.setdefault("MINIO_ENDPOINT", "localhost:9000")
os.environ.setdefault("MINIO_ACCESS_KEY", "test")
os.environ.setdefault("MINIO_SECRET_KEY", "test")
os.environ.setdefault("FRONTEND_URL", "http://frontend.test")
os.environ.setdefault("CORS_ORIGINS", "http://frontend.test")
os.environ.setdefault("AUTH_RATE_LIMIT", "1000/minute")

# Environment must be configured before importing the application.
from app.main import app  # noqa: E402
from app.db.session import Base, get_db  # noqa: E402
from app.models.user import UserGroup, UserGroupEnum  # noqa: E402
from app.models.user import User  # noqa: E402
from app.models.movie import Certification, Movie  # noqa: E402
from app.core.security import create_access_token, get_password_hash  # noqa: E402

TEST_DATABASE_URL = "sqlite+aiosqlite:///:memory:"

engine = create_async_engine(TEST_DATABASE_URL, echo=False)
TestSessionLocal = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)


@pytest.fixture(scope="function")
async def db_session() -> AsyncGenerator[AsyncSession, None]:
    """Create test database session."""
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    async with TestSessionLocal() as session:
        # Create default user groups
        for group_name in [UserGroupEnum.USER, UserGroupEnum.MODERATOR, UserGroupEnum.ADMIN]:
            session.add(UserGroup(name=group_name.value))
        await session.commit()

        yield session

    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)


@pytest.fixture(autouse=True)
def disable_background_tasks(monkeypatch: pytest.MonkeyPatch) -> None:
    """Disable external Celery calls during API tests."""
    from app.services import auth_service

    monkeypatch.setattr(auth_service.send_activation_email, "delay", lambda *_: None)
    monkeypatch.setattr(auth_service.send_password_reset_email, "delay", lambda *_: None)


@pytest.fixture
async def client(db_session: AsyncSession) -> AsyncGenerator[AsyncClient, None]:
    """Create test client."""

    async def override_get_db():
        yield db_session

    app.dependency_overrides[get_db] = override_get_db

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        yield ac

    app.dependency_overrides.clear()


@pytest.fixture
async def user(db_session: AsyncSession) -> User:
    """Create an active regular user."""
    group = await db_session.scalar(select(UserGroup).where(UserGroup.name == UserGroupEnum.USER.value))
    user = User(
        email="user@example.com",
        hashed_password=get_password_hash("SecurePass123!"),
        is_active=True,
        group_id=group.id,
    )
    db_session.add(user)
    await db_session.commit()
    await db_session.refresh(user)
    return user


@pytest.fixture
async def moderator(db_session: AsyncSession) -> User:
    """Create an active moderator user."""
    group = await db_session.scalar(select(UserGroup).where(UserGroup.name == UserGroupEnum.MODERATOR.value))
    user = User(
        email="moderator@example.com",
        hashed_password=get_password_hash("SecurePass123!"),
        is_active=True,
        group_id=group.id,
    )
    db_session.add(user)
    await db_session.commit()
    await db_session.refresh(user)
    return user


@pytest.fixture
async def admin(db_session: AsyncSession) -> User:
    """Create an active administrator user."""
    group = await db_session.scalar(select(UserGroup).where(UserGroup.name == UserGroupEnum.ADMIN.value))
    user = User(
        email="admin@example.com",
        hashed_password=get_password_hash("SecurePass123!"),
        is_active=True,
        group_id=group.id,
    )
    db_session.add(user)
    await db_session.commit()
    await db_session.refresh(user)
    return user


@pytest.fixture
async def other_user(db_session: AsyncSession) -> User:
    """Create a second active regular user."""
    group = await db_session.scalar(select(UserGroup).where(UserGroup.name == UserGroupEnum.USER.value))
    user = User(
        email="other@example.com",
        hashed_password=get_password_hash("SecurePass123!"),
        is_active=True,
        group_id=group.id,
    )
    db_session.add(user)
    await db_session.commit()
    await db_session.refresh(user)
    return user


@pytest.fixture
def auth_headers(user: User) -> dict[str, str]:
    """Build bearer authorization headers for the regular user."""
    return {"Authorization": f"Bearer {create_access_token({'sub': str(user.id)})}"}


@pytest.fixture
def moderator_headers(moderator: User) -> dict[str, str]:
    """Build bearer authorization headers for the moderator."""
    return {"Authorization": f"Bearer {create_access_token({'sub': str(moderator.id)})}"}


@pytest.fixture
def admin_headers(admin: User) -> dict[str, str]:
    """Build bearer authorization headers for the administrator."""
    return {"Authorization": f"Bearer {create_access_token({'sub': str(admin.id)})}"}


@pytest.fixture
def other_auth_headers(other_user: User) -> dict[str, str]:
    """Build bearer authorization headers for the second user."""
    return {"Authorization": f"Bearer {create_access_token({'sub': str(other_user.id)})}"}


@pytest.fixture
async def movie(db_session: AsyncSession) -> Movie:
    """Create a movie with a required certification."""
    certification = Certification(name="PG-13")
    db_session.add(certification)
    await db_session.flush()
    movie = Movie(
        name="Test Movie",
        year=2024,
        time=120,
        imdb=8.0,
        votes=100,
        description="A movie created for tests.",
        price=9.99,
        certification_id=certification.id,
    )
    db_session.add(movie)
    await db_session.commit()
    await db_session.refresh(movie)
    return movie
