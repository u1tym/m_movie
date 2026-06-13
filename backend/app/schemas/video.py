from datetime import datetime

from pydantic import BaseModel, Field


class GenreBrief(BaseModel):
    genre_id: int
    name: str


class VideoSummaryResponse(BaseModel):
    video_id: int
    title: str
    description: str | None
    series_id: int | None
    series_title: str | None
    episode_number: int | None
    episode_title: str | None
    sort_order: int
    duration_ms: int
    mime_type: str
    file_size_bytes: int
    status: str
    genres: list[GenreBrief]
    has_thumbnail: bool
    position_ms: int | None
    completed: bool
    created_at: datetime
    updated_at: datetime


class VideoDetailResponse(VideoSummaryResponse):
    chunk_count: int
    last_played_at: datetime | None
    play_count: int


class VideoListResponse(BaseModel):
    items: list[VideoSummaryResponse]
    pagination: "PaginationMeta"


class VideoCreateRequest(BaseModel):
    title: str = Field(min_length=1, max_length=500)
    description: str | None = None
    series_id: int | None = None
    episode_number: int | None = Field(default=None, ge=1)
    episode_title: str | None = Field(default=None, max_length=500)
    sort_order: int = Field(default=0, ge=0)
    duration_ms: int = Field(ge=1, le=14_400_000)
    mime_type: str = Field(default="video/mp4", max_length=100)
    genre_ids: list[int] = Field(default_factory=list)


class VideoCreateResponse(BaseModel):
    video_id: int
    status: str
    title: str
    chunk_count: int
    created_at: datetime


class VideoUpdateRequest(BaseModel):
    title: str | None = Field(default=None, min_length=1, max_length=500)
    description: str | None = None
    series_id: int | None = None
    episode_number: int | None = Field(default=None, ge=1)
    episode_title: str | None = Field(default=None, max_length=500)
    sort_order: int | None = Field(default=None, ge=0)
    genre_ids: list[int] | None = None


class ChunkUploadResponse(BaseModel):
    video_id: int
    chunk_index: int
    byte_length: int
    uploaded_chunks: int


class VideoCompleteRequest(BaseModel):
    duration_ms: int = Field(ge=1, le=14_400_000)
    chunk_count: int = Field(ge=1)


class VideoCompleteResponse(BaseModel):
    video_id: int
    status: str
    duration_ms: int
    chunk_count: int
    file_size_bytes: int


class ChunkMetaResponse(BaseModel):
    chunk_index: int
    start_time_ms: int
    end_time_ms: int
    byte_length: int


class ChunkListResponse(BaseModel):
    video_id: int
    chunk_count: int
    items: list[ChunkMetaResponse]


class ThumbnailCreateResponse(BaseModel):
    video_id: int
    mime_type: str
    width: int | None
    height: int | None


class PaginationMeta(BaseModel):
    page: int
    per_page: int
    total_count: int
    total_pages: int


VideoListResponse.model_rebuild()
