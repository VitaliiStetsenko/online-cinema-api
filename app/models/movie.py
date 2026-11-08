"""Movie models for catalog."""

from __future__ import annotations

import uuid
from decimal import Decimal

from sqlalchemy import Column, DECIMAL, Float, ForeignKey, Integer, String, Table, Text, UniqueConstraint
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.session import Base

# Association tables
movie_genres = Table(
    "movie_genres",
    Base.metadata,
    Column("movie_id", Integer, ForeignKey("movies.id"), primary_key=True),
    Column("genre_id", Integer, ForeignKey("genres.id"), primary_key=True),
)

movie_directors = Table(
    "movie_directors",
    Base.metadata,
    Column("movie_id", Integer, ForeignKey("movies.id"), primary_key=True),
    Column("director_id", Integer, ForeignKey("directors.id"), primary_key=True),
)

movie_stars = Table(
    "movie_stars",
    Base.metadata,
    Column("movie_id", Integer, ForeignKey("movies.id"), primary_key=True),
    Column("star_id", Integer, ForeignKey("stars.id"), primary_key=True),
)


class Genre(Base):
    """Genres table."""

    __tablename__ = "genres"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    name: Mapped[str] = mapped_column(String(100), unique=True, nullable=False)

    movies: Mapped[list["Movie"]] = relationship(secondary=movie_genres, back_populates="genres")


class Star(Base):
    """Stars (actors) table."""

    __tablename__ = "stars"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    name: Mapped[str] = mapped_column(String(100), unique=True, nullable=False)

    movies: Mapped[list["Movie"]] = relationship(secondary=movie_stars, back_populates="stars")


class Director(Base):
    """Directors table."""

    __tablename__ = "directors"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    name: Mapped[str] = mapped_column(String(100), unique=True, nullable=False)

    movies: Mapped[list["Movie"]] = relationship(secondary=movie_directors, back_populates="directors")


class Certification(Base):
    """Certifications table."""

    __tablename__ = "certifications"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    name: Mapped[str] = mapped_column(String(100), unique=True, nullable=False)

    movies: Mapped[list["Movie"]] = relationship(back_populates="certification")


class Movie(Base):
    """Movies table."""

    __tablename__ = "movies"
    __table_args__ = (UniqueConstraint("name", "year", "time", name="uq_movie_name_year_time"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    uuid: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), default=uuid.uuid4, unique=True, nullable=False, index=True
    )
    name: Mapped[str] = mapped_column(String(250), nullable=False, index=True)
    year: Mapped[int] = mapped_column(Integer, nullable=False)
    time: Mapped[int] = mapped_column(Integer, nullable=False)
    imdb: Mapped[float] = mapped_column(Float, nullable=False)
    votes: Mapped[int] = mapped_column(Integer, nullable=False)
    meta_score: Mapped[float | None] = mapped_column(Float, nullable=True)
    gross: Mapped[float | None] = mapped_column(Float, nullable=True)
    description: Mapped[str] = mapped_column(Text, nullable=False)
    price: Mapped[Decimal | None] = mapped_column(DECIMAL(10, 2), nullable=True)
    certification_id: Mapped[int] = mapped_column(Integer, ForeignKey("certifications.id"), nullable=False)

    certification: Mapped[Certification] = relationship(back_populates="movies")
    genres: Mapped[list[Genre]] = relationship(secondary=movie_genres, back_populates="movies")
    directors: Mapped[list[Director]] = relationship(secondary=movie_directors, back_populates="movies")
    stars: Mapped[list[Star]] = relationship(secondary=movie_stars, back_populates="movies")
