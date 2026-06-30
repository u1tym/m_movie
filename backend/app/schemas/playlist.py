from datetime import datetime

from pydantic import BaseModel, Field


class PlaylistSummaryResponse(BaseModel):
    playlist_id: int
    name: str
    description: str | None
    item_count: int
    created_at: datetime
    updated_at: datetime


class PlaylistListResponse(BaseModel):
    items: list[PlaylistSummaryResponse]
    pagination: "PaginationMeta"


class PlaylistCreateRequest(BaseModel):
    name: str = Field(min_length=1, max_length=500)
    description: str | None = None


class PlaylistUpdateRequest(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=500)
    description: str | None = None


class PlaylistItemResponse(BaseModel):
    playlist_item_id: int
    video_id: int
    title: str
    duration_ms: int
    status: str
    sort_order: int
    has_thumbnail: bool


class PlaylistDetailResponse(BaseModel):
    playlist_id: int
    name: str
    description: str | None
    items: list[PlaylistItemResponse]
    created_at: datetime
    updated_at: datetime


class PlaylistItemInput(BaseModel):
    video_id: int


class PlaylistItemsUpdateRequest(BaseModel):
    items: list[PlaylistItemInput]


class PlaylistPlaybackStartRequest(BaseModel):
    resume: bool = True


class PlaylistPlaybackItemResponse(BaseModel):
    playlist_id: int
    playlist_item_id: int
    video_id: int
    title: str
    duration_ms: int
    mime_type: str
    chunk_count: int
    position_ms: int
    status: str
    sort_order: int
    stream_token: str
    start_chunk: "ChunkMetaResponse"
    has_next: bool
    has_prev: bool


class PlaylistNextItemResponse(BaseModel):
    has_next: bool
    item: PlaylistPlaybackItemResponse | None


class PlaylistPrevItemResponse(BaseModel):
    has_prev: bool
    item: PlaylistPlaybackItemResponse | None


class PaginationMeta(BaseModel):
    page: int
    per_page: int
    total_count: int
    total_pages: int


class ChunkMetaResponse(BaseModel):
    chunk_index: int
    start_time_ms: int
    end_time_ms: int
    byte_length: int


PlaylistListResponse.model_rebuild()
PlaylistPlaybackItemResponse.model_rebuild()
