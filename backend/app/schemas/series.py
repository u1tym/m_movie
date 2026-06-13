from datetime import datetime

from pydantic import BaseModel, Field


class SeriesResponse(BaseModel):
    series_id: int
    title: str
    description: str | None
    created_at: datetime
    updated_at: datetime


class SeriesListResponse(BaseModel):
    items: list[SeriesResponse]
    pagination: "PaginationMeta"


class SeriesCreateRequest(BaseModel):
    title: str = Field(min_length=1, max_length=500)
    description: str | None = None


class SeriesVideoBrief(BaseModel):
    video_id: int
    episode_number: int | None
    episode_title: str | None
    sort_order: int
    duration_ms: int
    status: str


class SeriesDetailResponse(SeriesResponse):
    videos: list[SeriesVideoBrief]


class PaginationMeta(BaseModel):
    page: int
    per_page: int
    total_count: int
    total_pages: int


SeriesListResponse.model_rebuild()
