"""Movie catalog API endpoints."""

from typing import TypeVar

from fastapi import APIRouter, Depends, HTTPException, Query, Response, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.dependencies import get_current_moderator
from app.db.session import get_db
from app.models.movie import Certification, Director, Genre, Star
from app.schemas.movie import (
    MovieCreate,
    GenreWithMovieCount,
    MovieListResponse,
    MovieResponse,
    MovieUpdate,
    NamedEntityCreate,
    NamedEntityResponse,
    NamedEntityUpdate,
)
from app.services import movie_service

router = APIRouter(prefix="/movies", tags=["Movies"])
catalog_router = APIRouter(prefix="/catalog", tags=["Catalog management"])

CatalogModel = TypeVar("CatalogModel", Genre, Director, Star, Certification)


async def _create_entity(model: type[CatalogModel], data: NamedEntityCreate, db: AsyncSession) -> CatalogModel:
    """Create a named catalog entity or return a validation error."""
    try:
        return await movie_service.create_named_entity(db, model, data.name)
    except ValueError as error:
        raise HTTPException(status_code=400, detail=str(error)) from error


async def _delete_entity(model: type[CatalogModel], entity_id: int, db: AsyncSession) -> Response:
    """Delete a named catalog entity by identifier."""
    entity = await movie_service.get_named_entity(db, model, entity_id)
    if not entity:
        raise HTTPException(status_code=404, detail="Catalog entity not found")
    try:
        await movie_service.delete_named_entity(db, entity)
    except ValueError as error:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(error)) from error
    return Response(status_code=status.HTTP_204_NO_CONTENT)


async def _update_entity(
    model: type[CatalogModel], entity_id: int, data: NamedEntityUpdate, db: AsyncSession
) -> CatalogModel:
    """Rename a named catalog entity by identifier."""
    entity = await movie_service.get_named_entity(db, model, entity_id)
    if not entity:
        raise HTTPException(status_code=404, detail="Catalog entity not found")
    try:
        return await movie_service.update_named_entity(db, entity, data.name)
    except ValueError as error:
        raise HTTPException(status_code=400, detail=str(error)) from error


@router.post("", response_model=MovieResponse, status_code=status.HTTP_201_CREATED)
async def create_movie(
    data: MovieCreate,
    db: AsyncSession = Depends(get_db),
    _=Depends(get_current_moderator),
):
    """Create a movie. Moderator access is required."""
    try:
        return await movie_service.create_movie(db, data)
    except ValueError as error:
        raise HTTPException(status_code=400, detail=str(error)) from error


@router.get("/{movie_id}", response_model=MovieResponse)
async def get_movie(movie_id: int, db: AsyncSession = Depends(get_db)):
    """Get a complete movie description."""
    movie = await movie_service.get_movie(db, movie_id)
    if not movie:
        raise HTTPException(status_code=404, detail="Movie not found")
    return movie


@router.get("", response_model=MovieListResponse)
async def list_movies(
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100),
    query: str | None = Query(default=None, max_length=250),
    genre_id: int | None = None,
    year_from: int | None = Query(default=None, ge=1888, le=2100),
    year_to: int | None = Query(default=None, ge=1888, le=2100),
    imdb_from: float | None = Query(default=None, ge=0, le=10),
    imdb_to: float | None = Query(default=None, ge=0, le=10),
    sort_by: str = Query(default="name", pattern="^(name|year|imdb|price|votes)$"),
    sort_order: str = Query(default="asc", pattern="^(asc|desc)$"),
    db: AsyncSession = Depends(get_db),
):
    """Browse movies with search, filters, sort order, and pagination."""
    if year_from and year_to and year_from > year_to:
        raise HTTPException(status_code=400, detail="year_from cannot exceed year_to")
    if imdb_from and imdb_to and imdb_from > imdb_to:
        raise HTTPException(status_code=400, detail="imdb_from cannot exceed imdb_to")
    items, total = await movie_service.list_movies(
        db,
        page,
        page_size,
        query,
        genre_id,
        year_from,
        year_to,
        imdb_from,
        imdb_to,
        sort_by,
        sort_order,
    )
    return {"items": items, "total": total, "page": page, "page_size": page_size}


@router.put("/{movie_id}", response_model=MovieResponse)
async def update_movie(
    movie_id: int,
    data: MovieUpdate,
    db: AsyncSession = Depends(get_db),
    _=Depends(get_current_moderator),
):
    """Update a movie. Moderator access is required."""
    movie = await movie_service.get_movie(db, movie_id)
    if not movie:
        raise HTTPException(status_code=404, detail="Movie not found")
    try:
        return await movie_service.update_movie(db, movie, data)
    except ValueError as error:
        raise HTTPException(status_code=400, detail=str(error)) from error


@router.delete("/{movie_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_movie(
    movie_id: int,
    db: AsyncSession = Depends(get_db),
    _=Depends(get_current_moderator),
):
    """Delete a movie that is not present in user carts."""
    movie = await movie_service.get_movie(db, movie_id)
    if not movie:
        raise HTTPException(status_code=404, detail="Movie not found")
    try:
        await movie_service.delete_movie(db, movie)
    except ValueError as error:
        raise HTTPException(status_code=400, detail=str(error)) from error
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@catalog_router.get("/genres", response_model=list[NamedEntityResponse])
async def list_genres(db: AsyncSession = Depends(get_db)):
    """List all movie genres."""
    return await movie_service.list_named_entities(db, Genre)


@catalog_router.get("/genres/with-counts", response_model=list[GenreWithMovieCount])
async def list_genres_with_counts(db: AsyncSession = Depends(get_db)):
    """List genres with the number of assigned movies."""
    rows = await movie_service.list_genres_with_counts(db)
    return [{"id": genre.id, "name": genre.name, "movie_count": movie_count} for genre, movie_count in rows]


@catalog_router.post("/genres", response_model=NamedEntityResponse, status_code=201)
async def create_genre(data: NamedEntityCreate, db: AsyncSession = Depends(get_db), _=Depends(get_current_moderator)):
    """Create a genre. Moderator access is required."""
    return await _create_entity(Genre, data, db)


@catalog_router.delete("/genres/{entity_id}", status_code=204)
async def delete_genre(entity_id: int, db: AsyncSession = Depends(get_db), _=Depends(get_current_moderator)):
    """Delete a genre. Moderator access is required."""
    return await _delete_entity(Genre, entity_id, db)


@catalog_router.put("/genres/{entity_id}", response_model=NamedEntityResponse)
async def update_genre(
    entity_id: int, data: NamedEntityUpdate, db: AsyncSession = Depends(get_db), _=Depends(get_current_moderator)
):
    """Rename a genre. Moderator access is required."""
    return await _update_entity(Genre, entity_id, data, db)


@catalog_router.get("/directors", response_model=list[NamedEntityResponse])
async def list_directors(db: AsyncSession = Depends(get_db)):
    """List all directors."""
    return await movie_service.list_named_entities(db, Director)


@catalog_router.post("/directors", response_model=NamedEntityResponse, status_code=201)
async def create_director(
    data: NamedEntityCreate, db: AsyncSession = Depends(get_db), _=Depends(get_current_moderator)
):
    """Create a director. Moderator access is required."""
    return await _create_entity(Director, data, db)


@catalog_router.delete("/directors/{entity_id}", status_code=204)
async def delete_director(entity_id: int, db: AsyncSession = Depends(get_db), _=Depends(get_current_moderator)):
    """Delete a director. Moderator access is required."""
    return await _delete_entity(Director, entity_id, db)


@catalog_router.put("/directors/{entity_id}", response_model=NamedEntityResponse)
async def update_director(
    entity_id: int, data: NamedEntityUpdate, db: AsyncSession = Depends(get_db), _=Depends(get_current_moderator)
):
    """Rename a director. Moderator access is required."""
    return await _update_entity(Director, entity_id, data, db)


@catalog_router.get("/stars", response_model=list[NamedEntityResponse])
async def list_stars(db: AsyncSession = Depends(get_db)):
    """List all actors."""
    return await movie_service.list_named_entities(db, Star)


@catalog_router.post("/stars", response_model=NamedEntityResponse, status_code=201)
async def create_star(data: NamedEntityCreate, db: AsyncSession = Depends(get_db), _=Depends(get_current_moderator)):
    """Create an actor. Moderator access is required."""
    return await _create_entity(Star, data, db)


@catalog_router.delete("/stars/{entity_id}", status_code=204)
async def delete_star(entity_id: int, db: AsyncSession = Depends(get_db), _=Depends(get_current_moderator)):
    """Delete an actor. Moderator access is required."""
    return await _delete_entity(Star, entity_id, db)


@catalog_router.put("/stars/{entity_id}", response_model=NamedEntityResponse)
async def update_star(
    entity_id: int, data: NamedEntityUpdate, db: AsyncSession = Depends(get_db), _=Depends(get_current_moderator)
):
    """Rename an actor. Moderator access is required."""
    return await _update_entity(Star, entity_id, data, db)


@catalog_router.get("/certifications", response_model=list[NamedEntityResponse])
async def list_certifications(db: AsyncSession = Depends(get_db)):
    """List all age certifications."""
    return await movie_service.list_named_entities(db, Certification)


@catalog_router.post("/certifications", response_model=NamedEntityResponse, status_code=201)
async def create_certification(
    data: NamedEntityCreate, db: AsyncSession = Depends(get_db), _=Depends(get_current_moderator)
):
    """Create a certification. Moderator access is required."""
    return await _create_entity(Certification, data, db)


@catalog_router.delete("/certifications/{entity_id}", status_code=204)
async def delete_certification(entity_id: int, db: AsyncSession = Depends(get_db), _=Depends(get_current_moderator)):
    """Delete a certification. Moderator access is required."""
    return await _delete_entity(Certification, entity_id, db)


@catalog_router.put("/certifications/{entity_id}", response_model=NamedEntityResponse)
async def update_certification(
    entity_id: int, data: NamedEntityUpdate, db: AsyncSession = Depends(get_db), _=Depends(get_current_moderator)
):
    """Rename a certification. Moderator access is required."""
    return await _update_entity(Certification, entity_id, data, db)
