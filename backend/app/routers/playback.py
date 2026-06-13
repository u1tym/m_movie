from fastapi import APIRouter, Depends, Query, Request
from sqlalchemy.orm import Session

from app.database import get_db
from app.dependencies import get_aid_dependency
from app.schemas.playback import (
    HistoryListResponse,
    NextVideoResponse,
    PlaybackSeekResponse,
    PlaybackStartRequest,
    PlaybackStartResponse,
    PlaybackStateResponse,
    PlaybackStateUpdateRequest,
)
from app.services import playback_service

router = APIRouter(tags=["playback"])


@router.post("/videos/{video_id}/playback/start", response_model=PlaybackStartResponse)
def start_playback(
    video_id: int,
    body: PlaybackStartRequest,
    db: Session = Depends(get_db),
    aid: int = Depends(get_aid_dependency()),
) -> PlaybackStartResponse:
    return playback_service.start_playback(db, aid, video_id, body)


@router.get("/videos/{video_id}/playback/seek", response_model=PlaybackSeekResponse)
def seek_playback(
    video_id: int,
    request: Request,
    position_ms: int = Query(..., ge=0),
    db: Session = Depends(get_db),
    aid: int = Depends(get_aid_dependency()),
) -> PlaybackSeekResponse:
    base_path = request.url.path.rsplit("/videos/", 1)[0]
    return playback_service.seek_playback(db, aid, video_id, position_ms, base_path)


@router.get("/videos/{video_id}/playback/state", response_model=PlaybackStateResponse)
def get_playback_state(
    video_id: int,
    db: Session = Depends(get_db),
    aid: int = Depends(get_aid_dependency()),
) -> PlaybackStateResponse:
    return playback_service.get_playback_state(db, aid, video_id)


@router.put("/videos/{video_id}/playback/state", response_model=PlaybackStateResponse)
def update_playback_state(
    video_id: int,
    body: PlaybackStateUpdateRequest,
    db: Session = Depends(get_db),
    aid: int = Depends(get_aid_dependency()),
) -> PlaybackStateResponse:
    return playback_service.update_playback_state(db, aid, video_id, body)


@router.get("/videos/{video_id}/next", response_model=NextVideoResponse)
def get_next_video(
    video_id: int,
    db: Session = Depends(get_db),
    aid: int = Depends(get_aid_dependency()),
) -> NextVideoResponse:
    return playback_service.get_next_video(db, aid, video_id)


@router.get("/playback/history", response_model=HistoryListResponse)
def list_history(
    page: int = Query(1, ge=1),
    per_page: int = Query(20, ge=1, le=100),
    db: Session = Depends(get_db),
    aid: int = Depends(get_aid_dependency()),
) -> HistoryListResponse:
    return playback_service.list_history(db, aid, page, per_page)
