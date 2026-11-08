"""Pydantic schemas for the movie catalog."""

from decimal import Decimal
from typing import Optional
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field


class NamedEntityCreate(BaseModel):
    """Input schema for a named catalog entity."""

    name: str = Field(min_length=1, max_length=100)


class NamedEntityUpdate(BaseModel):
    """Input schema for renaming a catalog entity."""

    name: str = Field(min_length=1, max_length=100)


class NamedEntityResponse(BaseModel):
    """Response schema for a named catalog entity."""

    id: int
    name: str

    model_config = ConfigDict(from_attributes=True)


class MovieCreate(BaseModel):
    """Input schema for creating a movie."""

    name: str = Field(min_length=1, max_length=250)
    year: int = Field(ge=1888, le=2100)
    time: int = Field(gt=0, le=1000)
    imdb: float = Field(ge=0, le=10)
    votes: int = Field(ge=0)
    meta_score: Optional[float] = Field(default=None, ge=0, le=100)
    gross: Optional[float] = Field(default=None, ge=0)
    description: str = Field(min_length=1)
    price: Decimal = Field(ge=0, max_digits=10, decimal_places=2)
    certification_id: int
    genre_ids: list[int] = Field(default_factory=list)
    director_ids: list[int] = Field(default_factory=list)
    star_ids: list[int] = Field(default_factory=list)


class MovieUpdate(BaseModel):
    """Input schema for updating a movie."""

    name: Optional[str] = Field(default=None, min_length=1, max_length=250)
    year: Optional[int] = Field(default=None, ge=1888, le=2100)
    time: Optional[int] = Field(default=None, gt=0, le=1000)
    imdb: Optional[float] = Field(default=None, ge=0, le=10)
    votes: Optional[int] = Field(default=None, ge=0)
    meta_score: Optional[float] = Field(default=None, ge=0, le=100)
    gross: Optional[float] = Field(default=None, ge=0)
    description: Optional[str] = Field(default=None, min_length=1)
    price: Optional[Decimal] = Field(default=None, ge=0, max_digits=10, decimal_places=2)
    certification_id: Optional[int] = None
    genre_ids: Optional[list[int]] = None
    director_ids: Optional[list[int]] = None
    star_ids: Optional[list[int]] = None


class MovieResponse(BaseModel):
    """Response schema for a movie."""

    id: int
    uuid: UUID
    name: str
    year: int
    time: int
    imdb: float
    votes: int
    meta_score: Optional[float]
    gross: Optional[float]
    description: str
    price: Decimal
    certification: NamedEntityResponse
    genres: list[NamedEntityResponse]
    directors: list[NamedEntityResponse]
    stars: list[NamedEntityResponse]

    model_config = ConfigDict(from_attributes=True)


class MovieListResponse(BaseModel):
    """Paginated movie catalog response."""

    items: list[MovieResponse]
    total: int
    page: int
    page_size: int


class GenreWithMovieCount(BaseModel):
    """Genre with the number of linked movies."""

    id: int
    name: str
    movie_count: int
