"""Tests for administration, reactions, notifications, and protected docs."""

from io import BytesIO

from httpx import AsyncClient
from PIL import Image

from app.models.movie import Movie
from app.models.user import User


async def test_admin_manages_users(client: AsyncClient, admin_headers: dict[str, str], user: User) -> None:
    """Only administrators can list users and change account state."""
    listed = await client.get("/api/users", headers=admin_headers)
    assert listed.status_code == 200
    assert listed.json()[1]["email"] == "user@example.com"

    updated = await client.patch(
        f"/api/users/{user.id}",
        headers=admin_headers,
        json={"group": "moderator", "is_active": False},
    )
    assert updated.status_code == 200
    assert updated.json()["group_name"] == "moderator"
    assert updated.json()["is_active"] is False


async def test_movie_reactions_and_comment_notifications(
    client: AsyncClient,
    auth_headers: dict[str, str],
    other_auth_headers: dict[str, str],
    movie: Movie,
) -> None:
    """Movie reactions and comment activity create notification records."""
    reaction = await client.put(f"/api/movies/{movie.id}/reaction?is_like=true", headers=auth_headers)
    assert reaction.status_code == 200
    assert reaction.json()["likes_count"] == 1

    comment = await client.post(
        f"/api/movies/{movie.id}/comments", headers=auth_headers, json={"text": "Original comment"}
    )
    comment_id = comment.json()["id"]
    replied = await client.post(
        f"/api/movies/{movie.id}/comments",
        headers=other_auth_headers,
        json={"text": "Reply", "parent_comment_id": comment_id},
    )
    assert replied.status_code == 201
    await client.put(f"/api/comments/{comment_id}/reaction?is_like=true", headers=other_auth_headers)

    notifications = await client.get("/api/notifications", headers=auth_headers)
    assert notifications.status_code == 200
    assert len(notifications.json()) == 2
    notification_id = notifications.json()[0]["id"]
    read = await client.patch(f"/api/notifications/{notification_id}/read", headers=auth_headers)
    assert read.status_code == 200
    assert read.json()["is_read"] is True


async def test_swagger_is_public(client: AsyncClient) -> None:
    """Swagger and OpenAPI schema are available without authentication."""
    assert (await client.get("/docs")).status_code == 200
    assert (await client.get("/openapi.json")).status_code == 200


async def test_upload_avatar_validates_and_stores_file(
    client: AsyncClient, auth_headers: dict[str, str], monkeypatch
) -> None:
    """Avatar endpoint validates type and stores the returned object key."""
    monkeypatch.setattr("app.api.users.upload_avatar", lambda *_: "avatars/test-avatar.png")
    invalid = await client.post(
        "/api/users/me/avatar",
        headers=auth_headers,
        files={"avatar": ("avatar.txt", b"text", "text/plain")},
    )
    assert invalid.status_code == 400

    image = BytesIO()
    Image.new("RGB", (1, 1)).save(image, format="PNG")
    uploaded = await client.post(
        "/api/users/me/avatar",
        headers=auth_headers,
        files={"avatar": ("avatar.png", image.getvalue(), "image/png")},
    )
    assert uploaded.status_code == 200
    assert uploaded.json()["avatar"] == "avatars/test-avatar.png"
