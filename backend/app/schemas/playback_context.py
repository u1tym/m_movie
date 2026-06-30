from datetime import datetime

from pydantic import BaseModel


class LastVideoContextResponse(BaseModel):
    video_id: int
    title: str
    duration_ms: int
    position_ms: int
    updated_at: datetime


class LastPlaylistContextResponse(BaseModel):
    playlist_id: int
    playlist_name: str
    playlist_item_id: int
    video_id: int
    video_title: str
    duration_ms: int
    position_ms: int
    updated_at: datetime


class LastPlaybackResponse(BaseModel):
    video: LastVideoContextResponse | None = None
    playlist: LastPlaylistContextResponse | None = None
