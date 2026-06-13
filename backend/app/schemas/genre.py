from datetime import datetime

from pydantic import BaseModel, Field


class GenreResponse(BaseModel):
    genre_id: int
    name: str
    sort_order: int
    is_system: bool


class GenreListResponse(BaseModel):
    items: list[GenreResponse]


class GenreCreateRequest(BaseModel):
    name: str = Field(min_length=1, max_length=100)
    sort_order: int = Field(default=0, ge=0)
