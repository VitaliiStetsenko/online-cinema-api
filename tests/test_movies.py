"""Integration tests for movie catalog endpoints."""

from httpx import AsyncClient

from app.models.movie import Movie


async def test_moderator_manages_catalog_entities(client: AsyncClient, moderator_headers: dict[str, str]) -> None:
    """Moderators can create and list catalog entities."""
    created = await client.post("/api/catalog/certifications", json={"name": "PG-13"}, headers=moderator_headers)
    assert created.status_code == 201
    assert created.json()["name"] == "PG-13"

    response = await client.get("/api/catalog/certifications")
    assert response.status_code == 200
    assert response.json() == [{"id": created.json()["id"], "name": "PG-13"}]

    renamed = await client.put(
        f"/api/catalog/certifications/{created.json()['id']}",
        json={"name": "PG"},
        headers=moderator_headers,
    )
    assert renamed.status_code == 200
    assert renamed.json()["name"] == "PG"


async def test_regular_user_cannot_create_genre(client: AsyncClient, auth_headers: dict[str, str]) -> None:
    """Regular users cannot change the catalog."""
    response = await client.post("/api/catalog/genres", json={"name": "Drama"}, headers=auth_headers)
    assert response.status_code == 403


async def test_movie_crud_and_search(client: AsyncClient, moderator_headers: dict[str, str]) -> None:
    """Moderators create movies and everyone can find them."""
    certification = await client.post("/api/catalog/certifications", json={"name": "R"}, headers=moderator_headers)
    genre = await client.post("/api/catalog/genres", json={"name": "Action"}, headers=moderator_headers)
    director = await client.post("/api/catalog/directors", json={"name": "Jane Director"}, headers=moderator_headers)
    star = await client.post("/api/catalog/stars", json={"name": "John Star"}, headers=moderator_headers)

    response = await client.post(
        "/api/movies",
        headers=moderator_headers,
        json={
            "name": "Action Test",
            "year": 2020,
            "time": 100,
            "imdb": 8.4,
            "votes": 250,
            "description": "Action story starring John Star.",
            "price": "12.50",
            "certification_id": certification.json()["id"],
            "genre_ids": [genre.json()["id"]],
            "director_ids": [director.json()["id"]],
            "star_ids": [star.json()["id"]],
        },
    )
    assert response.status_code == 201
    movie_id = response.json()["id"]

    catalog = await client.get("/api/movies", params={"query": "John", "genre_id": genre.json()["id"]})
    assert catalog.status_code == 200
    assert catalog.json()["total"] == 1
    assert catalog.json()["items"][0]["id"] == movie_id

    updated = await client.put(f"/api/movies/{movie_id}", json={"price": "15.00"}, headers=moderator_headers)
    assert updated.status_code == 200
    assert updated.json()["price"] == "15.00"

    deleted = await client.delete(f"/api/movies/{movie_id}", headers=moderator_headers)
    assert deleted.status_code == 204
    assert (await client.get(f"/api/movies/{movie_id}")).status_code == 404


async def test_genres_include_movie_counts(client: AsyncClient, movie: Movie) -> None:
    """Genre count endpoint returns an empty count for unassigned genres."""
    response = await client.get("/api/catalog/genres/with-counts")
    assert response.status_code == 200
    assert response.json() == []


async def test_deleting_used_certification_returns_conflict(
    client: AsyncClient, moderator_headers: dict[str, str], movie: Movie
) -> None:
    """Catalog entries referenced by movies cannot be deleted."""
    response = await client.delete(f"/api/catalog/certifications/{movie.certification_id}", headers=moderator_headers)

    assert response.status_code == 409
