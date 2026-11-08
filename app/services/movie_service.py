"""Services for movie catalog management."""

from collections.abc import Sequence
from typing import TypeVar

from sqlalchemy import func, or_, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.cart import CartItem
from app.models.movie import Certification, Director, Genre, Movie, Star
from app.schemas.movie import MovieCreate, MovieUpdate

CatalogModel = TypeVar("CatalogModel", Genre, Director, Star, Certification)


async def get_named_entity(db: AsyncSession, model: type[CatalogModel], entity_id: int) -> CatalogModel | None:
    """Find a catalog entity by its identifier."""
    return await db.get(model, entity_id)


async def create_named_entity(db: AsyncSession, model: type[CatalogModel], name: str) -> CatalogModel:
    """Create a genre, star, director, or certification."""
    exists = await db.scalar(select(model).where(model.name.ilike(name)))
    if exists:
        raise ValueError("Entity with this name already exists")

    entity = model(name=name)
    db.add(entity)
    await db.commit()
    await db.refresh(entity)
    return entity


async def list_named_entities(db: AsyncSession, model: type[CatalogModel]) -> Sequence[CatalogModel]:
    """List catalog entities alphabetically."""
    result = await db.execute(select(model).order_by(model.name))
    return result.scalars().all()


async def delete_named_entity(db: AsyncSession, entity: CatalogModel) -> None:
    """Delete a catalog entity."""
    try:
        await db.delete(entity)
        await db.commit()
    except IntegrityError as error:
        await db.rollback()
        raise ValueError("Catalog entity cannot be deleted because it is used by movies") from error


async def update_named_entity(db: AsyncSession, entity: CatalogModel, name: str) -> CatalogModel:
    """Rename a genre, star, director, or certification."""
    model = type(entity)
    exists = await db.scalar(select(model).where(model.name.ilike(name)))
    if exists and exists.id != entity.id:
        raise ValueError("Entity with this name already exists")
    entity.name = name
    await db.commit()
    await db.refresh(entity)
    return entity


async def _get_entities(db: AsyncSession, model: type[CatalogModel], ids: list[int]) -> Sequence[CatalogModel]:
    """Load and validate entities selected for a movie."""
    if not ids:
        return []

    result = await db.execute(select(model).where(model.id.in_(ids)))
    entities = result.scalars().all()
    if len(entities) != len(set(ids)):
        raise ValueError(f"One or more {model.__tablename__} do not exist")
    return entities


async def get_movie(db: AsyncSession, movie_id: int) -> Movie | None:
    """Get a movie with all catalog relations."""
    statement = (
        select(Movie)
        .where(Movie.id == movie_id)
        .options(
            selectinload(Movie.certification),
            selectinload(Movie.genres),
            selectinload(Movie.directors),
            selectinload(Movie.stars),
        )
    )
    return await db.scalar(statement)


async def list_movies(
    db: AsyncSession,
    page: int,
    page_size: int,
    query: str | None = None,
    genre_id: int | None = None,
    year_from: int | None = None,
    year_to: int | None = None,
    imdb_from: float | None = None,
    imdb_to: float | None = None,
    sort_by: str = "name",
    sort_order: str = "asc",
) -> tuple[Sequence[Movie], int]:
    """List movies with search, filtering, sorting, and pagination."""
    filters = []
    if query:
        pattern = f"%{query.strip()}%"
        filters.append(
            or_(
                Movie.name.ilike(pattern),
                Movie.description.ilike(pattern),
                Movie.stars.any(Star.name.ilike(pattern)),
                Movie.directors.any(Director.name.ilike(pattern)),
            )
        )
    if genre_id is not None:
        filters.append(Movie.genres.any(Genre.id == genre_id))
    if year_from is not None:
        filters.append(Movie.year >= year_from)
    if year_to is not None:
        filters.append(Movie.year <= year_to)
    if imdb_from is not None:
        filters.append(Movie.imdb >= imdb_from)
    if imdb_to is not None:
        filters.append(Movie.imdb <= imdb_to)

    total = await db.scalar(select(func.count(Movie.id)).where(*filters)) or 0
    sort_column = getattr(Movie, sort_by)
    ordering = sort_column.desc() if sort_order == "desc" else sort_column.asc()
    statement = (
        select(Movie)
        .where(*filters)
        .options(
            selectinload(Movie.certification),
            selectinload(Movie.genres),
            selectinload(Movie.directors),
            selectinload(Movie.stars),
        )
        .order_by(ordering, Movie.id)
        .offset((page - 1) * page_size)
        .limit(page_size)
    )
    result = await db.execute(statement)
    return result.scalars().unique().all(), total


async def list_genres_with_counts(
    db: AsyncSession,
) -> Sequence[tuple[Genre, int]]:
    """List genres with their linked movie counts."""
    statement = select(Genre, func.count(Movie.id)).outerjoin(Genre.movies).group_by(Genre.id).order_by(Genre.name)
    result = await db.execute(statement)
    return result.all()


async def create_movie(db: AsyncSession, data: MovieCreate) -> Movie:
    """Create a movie and attach its catalog relations."""
    certification = await get_named_entity(db, Certification, data.certification_id)
    if not certification:
        raise ValueError("Certification not found")

    movie = Movie(
        **data.model_dump(exclude={"genre_ids", "director_ids", "star_ids"}),
        genres=await _get_entities(db, Genre, data.genre_ids),
        directors=await _get_entities(db, Director, data.director_ids),
        stars=await _get_entities(db, Star, data.star_ids),
    )
    db.add(movie)
    try:
        await db.commit()
    except IntegrityError as error:
        await db.rollback()
        raise ValueError("Movie with this name, year, and duration already exists") from error
    result = await get_movie(db, movie.id)
    if not result:
        raise RuntimeError("Movie was not created")
    return result


async def update_movie(db: AsyncSession, movie: Movie, data: MovieUpdate) -> Movie:
    """Update movie fields and catalog relations."""
    update_data = data.model_dump(exclude_unset=True)
    for relation, model, field in (
        ("genres", Genre, "genre_ids"),
        ("directors", Director, "director_ids"),
        ("stars", Star, "star_ids"),
    ):
        ids = update_data.pop(field, None)
        if ids is not None:
            setattr(movie, relation, await _get_entities(db, model, ids))

    if "certification_id" in update_data:
        certification = await get_named_entity(db, Certification, update_data["certification_id"])
        if not certification:
            raise ValueError("Certification not found")

    for field, value in update_data.items():
        setattr(movie, field, value)

    try:
        await db.commit()
    except IntegrityError as error:
        await db.rollback()
        raise ValueError("Movie with this name, year, and duration already exists") from error
    result = await get_movie(db, movie.id)
    if not result:
        raise RuntimeError("Movie was not found after update")
    return result


async def delete_movie(db: AsyncSession, movie: Movie) -> None:
    """Delete a movie not referenced by a cart."""
    cart_item = await db.scalar(select(CartItem.id).where(CartItem.movie_id == movie.id))
    if cart_item:
        raise ValueError("Movie cannot be deleted while it is in user carts")
    await db.delete(movie)
    await db.commit()
