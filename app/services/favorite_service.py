"""Services for user favorite movies."""

from collections.abc import Sequence

from sqlalchemy import func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.interaction import Favorite
from app.models.movie import Director, Genre, Movie, Star


async def add_favorite(db: AsyncSession, user_id: int, movie_id: int) -> Favorite:
    """Add a movie to the user's favorites."""
    movie = await db.get(Movie, movie_id)
    if not movie:
        raise ValueError("Movie not found")

    existing = await db.scalar(select(Favorite).where(Favorite.user_id == user_id, Favorite.movie_id == movie_id))
    if existing:
        raise ValueError("Movie is already in favorites")

    favorite = Favorite(user_id=user_id, movie_id=movie_id)
    db.add(favorite)
    await db.commit()
    result = await get_favorite(db, user_id, movie_id)
    if not result:
        raise RuntimeError("Favorite was not created")
    return result


async def get_favorite(db: AsyncSession, user_id: int, movie_id: int) -> Favorite | None:
    """Get a favorite entry with the movie details."""
    statement = (
        select(Favorite)
        .where(Favorite.user_id == user_id, Favorite.movie_id == movie_id)
        .options(
            selectinload(Favorite.movie).selectinload(Movie.certification),
            selectinload(Favorite.movie).selectinload(Movie.genres),
            selectinload(Favorite.movie).selectinload(Movie.directors),
            selectinload(Favorite.movie).selectinload(Movie.stars),
        )
    )
    return await db.scalar(statement)


async def list_favorites(
    db: AsyncSession,
    user_id: int,
    page: int,
    page_size: int,
    query: str | None = None,
    genre_id: int | None = None,
    year_from: int | None = None,
    year_to: int | None = None,
    imdb_from: float | None = None,
    imdb_to: float | None = None,
    sort_by: str = "added_at",
    sort_order: str = "desc",
) -> tuple[Sequence[Favorite], int]:
    """List favorites using the same catalog search and filter options."""
    filters = [Favorite.user_id == user_id]
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

    total = await db.scalar(select(func.count(Favorite.id)).join(Favorite.movie).where(*filters)) or 0
    sort_column = Favorite.added_at if sort_by == "added_at" else getattr(Movie, sort_by)
    ordering = sort_column.desc() if sort_order == "desc" else sort_column.asc()
    statement = (
        select(Favorite)
        .join(Favorite.movie)
        .where(*filters)
        .options(
            selectinload(Favorite.movie).selectinload(Movie.certification),
            selectinload(Favorite.movie).selectinload(Movie.genres),
            selectinload(Favorite.movie).selectinload(Movie.directors),
            selectinload(Favorite.movie).selectinload(Movie.stars),
        )
        .order_by(ordering, Favorite.id)
        .offset((page - 1) * page_size)
        .limit(page_size)
    )
    result = await db.execute(statement)
    return result.scalars().unique().all(), total


async def remove_favorite(db: AsyncSession, user_id: int, movie_id: int) -> bool:
    """Remove a movie from the user's favorites."""
    favorite = await db.scalar(select(Favorite).where(Favorite.user_id == user_id, Favorite.movie_id == movie_id))
    if not favorite:
        return False
    await db.delete(favorite)
    await db.commit()
    return True
