from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.database import get_db
from app.dependencies import get_aid_dependency
from app.schemas.playlist import (
    PlaylistCreateRequest,
    PlaylistDetailResponse,
    PlaylistItemsUpdateRequest,
    PlaylistListResponse,
    PlaylistNextItemResponse,
    PlaylistPlaybackItemResponse,
    PlaylistPlaybackStartRequest,
    PlaylistUpdateRequest,
)
from app.services import playlist_service

router = APIRouter(prefix="/playlists", tags=["playlists"])


@router.get("", response_model=PlaylistListResponse)
def list_playlists(
    page: int = Query(1, ge=1),
    per_page: int = Query(20, ge=1, le=100),
    db: Session = Depends(get_db),
    aid: int = Depends(get_aid_dependency()),
) -> PlaylistListResponse:
    return playlist_service.list_playlists(db, aid, page, per_page)


@router.post("", response_model=PlaylistDetailResponse, status_code=201)
def create_playlist(
    body: PlaylistCreateRequest,
    db: Session = Depends(get_db),
    aid: int = Depends(get_aid_dependency()),
) -> PlaylistDetailResponse:
    return playlist_service.create_playlist(db, aid, body)


@router.get("/{playlist_id}", response_model=PlaylistDetailResponse)
def get_playlist(
    playlist_id: int,
    db: Session = Depends(get_db),
    aid: int = Depends(get_aid_dependency()),
) -> PlaylistDetailResponse:
    return playlist_service.get_playlist_detail(db, aid, playlist_id)


@router.put("/{playlist_id}", response_model=PlaylistDetailResponse)
def update_playlist(
    playlist_id: int,
    body: PlaylistUpdateRequest,
    db: Session = Depends(get_db),
    aid: int = Depends(get_aid_dependency()),
) -> PlaylistDetailResponse:
    return playlist_service.update_playlist(db, aid, playlist_id, body)


@router.delete("/{playlist_id}", status_code=204)
def delete_playlist(
    playlist_id: int,
    db: Session = Depends(get_db),
    aid: int = Depends(get_aid_dependency()),
) -> None:
    playlist_service.delete_playlist(db, aid, playlist_id)


@router.put("/{playlist_id}/items", response_model=PlaylistDetailResponse)
def update_playlist_items(
    playlist_id: int,
    body: PlaylistItemsUpdateRequest,
    db: Session = Depends(get_db),
    aid: int = Depends(get_aid_dependency()),
) -> PlaylistDetailResponse:
    return playlist_service.update_playlist_items(db, aid, playlist_id, body)


@router.post("/{playlist_id}/playback/start", response_model=PlaylistPlaybackItemResponse)
def start_playlist_playback(
    playlist_id: int,
    body: PlaylistPlaybackStartRequest,
    db: Session = Depends(get_db),
    aid: int = Depends(get_aid_dependency()),
) -> PlaylistPlaybackItemResponse:
    return playlist_service.start_playlist_playback(db, aid, playlist_id, body)


@router.get("/{playlist_id}/items/{playlist_item_id}/next", response_model=PlaylistNextItemResponse)
def get_next_playlist_item(
    playlist_id: int,
    playlist_item_id: int,
    db: Session = Depends(get_db),
    aid: int = Depends(get_aid_dependency()),
) -> PlaylistNextItemResponse:
    return playlist_service.get_next_playlist_item(db, aid, playlist_id, playlist_item_id)


@router.put("/{playlist_id}/items/{playlist_item_id}/playback/state", status_code=204)
def save_playlist_playback_state(
    playlist_id: int,
    playlist_item_id: int,
    position_ms: int = Query(..., ge=0),
    db: Session = Depends(get_db),
    aid: int = Depends(get_aid_dependency()),
) -> None:
    playlist_service.save_playlist_playback_state(
        db, aid, playlist_id, playlist_item_id, position_ms
    )
