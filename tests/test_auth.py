"""Tests for authentication API."""

import pytest
from httpx import AsyncClient
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.user import ActivationToken, PasswordResetToken, User
from app.tasks.email_tasks import send_activation_email, send_password_reset_email


@pytest.mark.asyncio
async def test_register_user(client: AsyncClient):
    """Test user registration."""
    response = await client.post("/api/auth/register", json={"email": "test@example.com", "password": "SecurePass123!"})
    assert response.status_code == 201
    data = response.json()
    assert "message" in data
    assert data["email"] == "test@example.com"


@pytest.mark.asyncio
async def test_register_duplicate_email(client: AsyncClient):
    """Test registration with duplicate email."""
    await client.post("/api/auth/register", json={"email": "test@example.com", "password": "SecurePass123!"})
    response = await client.post(
        "/api/auth/register", json={"email": "test@example.com", "password": "AnotherPass123!"}
    )
    assert response.status_code == 400


@pytest.mark.asyncio
async def test_login_inactive_user(client: AsyncClient):
    """Test login with inactive account."""
    await client.post("/api/auth/register", json={"email": "test@example.com", "password": "SecurePass123!"})
    response = await client.post("/api/auth/login", json={"email": "test@example.com", "password": "SecurePass123!"})
    assert response.status_code == 401


async def test_activation_login_refresh_and_logout(client: AsyncClient, db_session: AsyncSession) -> None:
    """Activated users receive, refresh, and revoke JWT tokens."""
    await client.post("/api/auth/register", json={"email": "active@example.com", "password": "SecurePass123!"})
    activation = await db_session.scalar(select(ActivationToken).join(User).where(User.email == "active@example.com"))

    activated = await client.post(f"/api/auth/activate/{activation.token}")
    assert activated.status_code == 200
    assert (await client.post(f"/api/auth/activate/{activation.token}")).status_code == 400

    login = await client.post("/api/auth/login", json={"email": "active@example.com", "password": "SecurePass123!"})
    assert login.status_code == 200
    tokens = login.json()
    assert tokens["access_token"]
    assert tokens["refresh_token"]

    refresh_as_access = await client.post(
        "/api/auth/change-password",
        headers={"Authorization": f"Bearer {tokens['refresh_token']}"},
        json={"old_password": "SecurePass123!", "new_password": "ChangedPass123!"},
    )
    assert refresh_as_access.status_code == 401

    access_as_refresh = await client.post("/api/auth/refresh", json={"refresh_token": tokens["access_token"]})
    assert access_as_refresh.status_code == 401

    refreshed = await client.post("/api/auth/refresh", json={"refresh_token": tokens["refresh_token"]})
    assert refreshed.status_code == 200
    assert refreshed.json()["access_token"]

    logged_out = await client.post("/api/auth/logout", json={"refresh_token": tokens["refresh_token"]})
    assert logged_out.status_code == 200
    assert (await client.post("/api/auth/refresh", json={"refresh_token": tokens["refresh_token"]})).status_code == 401


async def test_password_change_and_reset(client: AsyncClient, db_session: AsyncSession) -> None:
    """Users can change and reset their password."""
    await client.post("/api/auth/register", json={"email": "password@example.com", "password": "SecurePass123!"})
    activation = await db_session.scalar(select(ActivationToken).join(User).where(User.email == "password@example.com"))
    await client.post(f"/api/auth/activate/{activation.token}")
    login = await client.post("/api/auth/login", json={"email": "password@example.com", "password": "SecurePass123!"})
    headers = {"Authorization": f"Bearer {login.json()['access_token']}"}

    wrong_old = await client.post(
        "/api/auth/change-password",
        headers=headers,
        json={"old_password": "WrongPass123!", "new_password": "ChangedPass123!"},
    )
    assert wrong_old.status_code == 400

    changed = await client.post(
        "/api/auth/change-password",
        headers=headers,
        json={"old_password": "SecurePass123!", "new_password": "ChangedPass123!"},
    )
    assert changed.status_code == 200
    assert (
        await client.post("/api/auth/login", json={"email": "password@example.com", "password": "ChangedPass123!"})
    ).status_code == 200

    requested = await client.post("/api/auth/request-password-reset", json={"email": "password@example.com"})
    assert requested.status_code == 200
    token = await db_session.scalar(select(PasswordResetToken).join(User).where(User.email == "password@example.com"))
    reset = await client.post("/api/auth/reset-password", json={"token": token.token, "new_password": "ResetPass123!"})
    assert reset.status_code == 200
    assert (
        await client.post("/api/auth/login", json={"email": "password@example.com", "password": "ResetPass123!"})
    ).status_code == 200


async def test_resend_activation_and_invalid_reset(client: AsyncClient, db_session: AsyncSession) -> None:
    """Inactive users can request a fresh activation token."""
    await client.post("/api/auth/register", json={"email": "resend@example.com", "password": "SecurePass123!"})
    initial = await db_session.scalar(select(ActivationToken).join(User).where(User.email == "resend@example.com"))
    resent = await client.post("/api/auth/resend-activation", json={"email": "resend@example.com"})
    assert resent.status_code == 200
    replacement = await db_session.scalar(select(ActivationToken).join(User).where(User.email == "resend@example.com"))
    assert replacement.token != initial.token
    assert (
        await client.post("/api/auth/reset-password", json={"token": "bad", "new_password": "ResetPass123!"})
    ).status_code == 400


def test_email_links_target_configured_frontend(monkeypatch: pytest.MonkeyPatch) -> None:
    """Activation and reset emails point to frontend pages rather than POST-only API routes."""
    sent_bodies: list[str] = []
    monkeypatch.setattr("app.tasks.email_tasks._send_email", lambda _, __, body: sent_bodies.append(body))

    send_activation_email.run("user@example.com", "activation-token")
    send_password_reset_email.run("user@example.com", "reset-token")

    assert "http://frontend.test/activate?token=activation-token" in sent_bodies[0]
    assert "http://frontend.test/reset-password?token=reset-token" in sent_bodies[1]
