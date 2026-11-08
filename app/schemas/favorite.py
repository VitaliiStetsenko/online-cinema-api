"""Pydantic schemas for favorite movies."""

from datetime import datetime

from pydantic import BaseModel, ConfigDict

from app.schemas.movie import MovieResponse


class FavoriteResponse(BaseModel):
    """Response schema for one favorite movie."""

    id: int
    added_at: datetime
    movie: MovieResponse

    model_config = ConfigDict(from_attributes=True)


class FavoriteListResponse(BaseModel):
    """Paginated favorite movies response."""

    items: list[FavoriteResponse]
    total: int
    page: int
    page_size: int
