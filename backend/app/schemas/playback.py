from datetime import datetime

from pydantic import BaseModel, Field


class PlaybackStartRequest(BaseModel):
    resume: bool = True


class ChunkMetaResponse(BaseModel):
    chunk_index: int
    start_time_ms: int
    end_time_ms: int
    byte_length: int


class PlaybackStartResponse(BaseModel):
    video_id: int
    title: str
    duration_ms: int
    mime_type: str
    chunk_count: int
    position_ms: int
    completed: bool
    status: str
    start_chunk: ChunkMetaResponse


class PlaybackSeekResponse(BaseModel):
    video_id: int
    position_ms: int
    chunk: ChunkMetaResponse
    chunk_url: str


class PlaybackStateUpdateRequest(BaseModel):
    position_ms: int = Field(ge=0)
    completed: bool | None = None


class PlaybackStateResponse(BaseModel):
    video_id: int
    position_ms: int
    completed: bool
    play_count: int
    last_played_at: datetime | None


class NextVideoBrief(BaseModel):
    video_id: int
    title: str
    episode_number: int | None
    sort_order: int
    duration_ms: int
    status: str


class NextVideoResponse(BaseModel):
    has_next: bool
    video: NextVideoBrief | None


class HistoryItemResponse(BaseModel):
    video_id: int
    title: str
    position_ms: int
    completed: bool
    duration_ms: int
    last_played_at: datetime


class HistoryListResponse(BaseModel):
    items: list[HistoryItemResponse]
    pagination: "PaginationMeta"


class PaginationMeta(BaseModel):
    page: int
    per_page: int
    total_count: int
    total_pages: int


HistoryListResponse.model_rebuild()
