from sqlalchemy import exists, func, select
from sqlalchemy.orm import Session, joinedload

from app.dependencies import AppError
from app.models import Playlist, PlaylistItem, Thumbnail, Video
from app.schemas import build_pagination, normalize_page
from app.schemas.playlist import (
    ChunkMetaResponse,
    PaginationMeta,
    PlaylistCreateRequest,
    PlaylistDetailResponse,
    PlaylistItemInput,
    PlaylistItemResponse,
    PlaylistItemsUpdateRequest,
    PlaylistListResponse,
    PlaylistNextItemResponse,
    PlaylistPlaybackItemResponse,
    PlaylistPlaybackStartRequest,
    PlaylistPrevItemResponse,
    PlaylistSummaryResponse,
    PlaylistUpdateRequest,
)
from app.security.stream_token import create_stream_token
from app.services.playback_context_service import upsert_playlist_context
from app.services.video_service import _get_owned_video, chunk_to_meta, find_chunk_at_position


def _get_owned_playlist(db: Session, aid: int, playlist_id: int) -> Playlist:
    playlist = db.get(Playlist, playlist_id)
    if playlist is None or playlist.aid != aid:
        raise AppError(code="NOT_FOUND", message="プレイリストが見つかりません", status_code=404)
    return playlist


def _item_has_thumbnail(db: Session, video_id: int) -> bool:
    return bool(db.scalar(select(exists().where(Thumbnail.video_id == video_id))))


def _to_item_response(db: Session, item: PlaylistItem) -> PlaylistItemResponse:
    video = item.video
    return PlaylistItemResponse(
        playlist_item_id=item.playlist_item_id,
        video_id=item.video_id,
        title=video.title,
        duration_ms=video.duration_ms,
        status=video.status,
        sort_order=item.sort_order,
        has_thumbnail=_item_has_thumbnail(db, item.video_id),
    )


def list_playlists(db: Session, aid: int, page: int, per_page: int) -> PlaylistListResponse:
    page, per_page, offset = normalize_page(page, per_page)
    base = select(Playlist).where(Playlist.aid == aid)
    total_count = db.scalar(select(func.count()).select_from(base.subquery())) or 0

    stmt = base.order_by(Playlist.updated_at.desc()).offset(offset).limit(per_page)
    playlists = db.scalars(stmt).all()

    items: list[PlaylistSummaryResponse] = []
    for p in playlists:
        count = db.scalar(
            select(func.count()).where(PlaylistItem.playlist_id == p.playlist_id)
        ) or 0
        items.append(
            PlaylistSummaryResponse(
                playlist_id=p.playlist_id,
                name=p.name,
                description=p.description,
                item_count=count,
                created_at=p.created_at,
                updated_at=p.updated_at,
            )
        )

    return PlaylistListResponse(
        items=items,
        pagination=PaginationMeta(**build_pagination(page, per_page, total_count).model_dump()),
    )


def create_playlist(db: Session, aid: int, body: PlaylistCreateRequest) -> PlaylistDetailResponse:
    playlist = Playlist(aid=aid, name=body.name, description=body.description)
    db.add(playlist)
    db.commit()
    db.refresh(playlist)
    return get_playlist_detail(db, aid, playlist.playlist_id)


def get_playlist_detail(db: Session, aid: int, playlist_id: int) -> PlaylistDetailResponse:
    playlist = _get_owned_playlist(db, aid, playlist_id)
    stmt = (
        select(PlaylistItem)
        .options(joinedload(PlaylistItem.video))
        .where(PlaylistItem.playlist_id == playlist_id)
        .order_by(PlaylistItem.sort_order)
    )
    items = [_to_item_response(db, i) for i in db.scalars(stmt).all()]
    return PlaylistDetailResponse(
        playlist_id=playlist.playlist_id,
        name=playlist.name,
        description=playlist.description,
        items=items,
        created_at=playlist.created_at,
        updated_at=playlist.updated_at,
    )


def update_playlist(
    db: Session, aid: int, playlist_id: int, body: PlaylistUpdateRequest
) -> PlaylistDetailResponse:
    playlist = _get_owned_playlist(db, aid, playlist_id)
    data = body.model_dump(exclude_unset=True)
    for key, value in data.items():
        setattr(playlist, key, value)
    db.commit()
    return get_playlist_detail(db, aid, playlist_id)


def delete_playlist(db: Session, aid: int, playlist_id: int) -> None:
    playlist = _get_owned_playlist(db, aid, playlist_id)
    db.delete(playlist)
    db.commit()


def _validate_video_ids(db: Session, aid: int, video_ids: list[int]) -> None:
    if not video_ids:
        return
    unique_ids = set(video_ids)
    count = db.scalar(
        select(func.count(Video.video_id)).where(
            Video.video_id.in_(unique_ids), Video.aid == aid, Video.status != "deleted"
        )
    ) or 0
    if count != len(unique_ids):
        raise AppError(code="NOT_FOUND", message="指定された動画が見つかりません", status_code=404)


def update_playlist_items(
    db: Session, aid: int, playlist_id: int, body: PlaylistItemsUpdateRequest
) -> PlaylistDetailResponse:
    _get_owned_playlist(db, aid, playlist_id)
    video_ids = [item.video_id for item in body.items]
    _validate_video_ids(db, aid, video_ids)

    db.query(PlaylistItem).filter(PlaylistItem.playlist_id == playlist_id).delete()
    for index, item in enumerate(body.items):
        db.add(
            PlaylistItem(
                playlist_id=playlist_id,
                video_id=item.video_id,
                sort_order=index,
            )
        )
    db.commit()
    return get_playlist_detail(db, aid, playlist_id)


def _get_item_in_playlist(
    db: Session, aid: int, playlist_id: int, playlist_item_id: int
) -> PlaylistItem:
    _get_owned_playlist(db, aid, playlist_id)
    item = db.scalars(
        select(PlaylistItem)
        .options(joinedload(PlaylistItem.video))
        .where(
            PlaylistItem.playlist_id == playlist_id,
            PlaylistItem.playlist_item_id == playlist_item_id,
        )
    ).first()
    if item is None:
        raise AppError(code="NOT_FOUND", message="プレイリスト項目が見つかりません", status_code=404)
    return item


def _build_playback_item(
    db: Session,
    aid: int,
    playlist_id: int,
    item: PlaylistItem,
    position_ms: int,
) -> PlaylistPlaybackItemResponse:
    video = _get_owned_video(db, aid, item.video_id)
    if video.status != "ready":
        raise AppError(
            code="UNPROCESSABLE",
            message="再生可能な動画ではありません",
            status_code=422,
        )

    chunk = find_chunk_at_position(db, item.video_id, position_ms)
    has_next = db.scalar(
        select(exists().where(
            PlaylistItem.playlist_id == playlist_id,
            PlaylistItem.sort_order > item.sort_order,
        ))
    )
    has_prev = db.scalar(
        select(exists().where(
            PlaylistItem.playlist_id == playlist_id,
            PlaylistItem.sort_order < item.sort_order,
        ))
    )

    return PlaylistPlaybackItemResponse(
        playlist_id=playlist_id,
        playlist_item_id=item.playlist_item_id,
        video_id=video.video_id,
        title=video.title,
        duration_ms=video.duration_ms,
        mime_type=video.mime_type,
        chunk_count=video.chunk_count,
        position_ms=position_ms,
        status=video.status,
        sort_order=item.sort_order,
        stream_token=create_stream_token(aid, video.video_id),
        start_chunk=ChunkMetaResponse(
            chunk_index=chunk.chunk_index,
            start_time_ms=chunk.start_time_ms,
            end_time_ms=chunk.end_time_ms,
            byte_length=chunk.byte_length,
        ),
        has_next=bool(has_next),
        has_prev=bool(has_prev),
    )


def start_playlist_playback(
    db: Session, aid: int, playlist_id: int, body: PlaylistPlaybackStartRequest
) -> PlaylistPlaybackItemResponse:
    _get_owned_playlist(db, aid, playlist_id)

    if body.resume:
        from app.models import PlaybackContext

        ctx = db.get(PlaybackContext, aid)
        if (
            ctx
            and ctx.last_playlist_id == playlist_id
            and ctx.last_playlist_item_id is not None
        ):
            item = _get_item_in_playlist(db, aid, playlist_id, ctx.last_playlist_item_id)
            position_ms = ctx.last_playlist_position_ms
            result = _build_playback_item(db, aid, playlist_id, item, position_ms)
            upsert_playlist_context(
                db, aid, playlist_id, item.playlist_item_id, position_ms
            )
            db.commit()
            return result

    first = db.scalars(
        select(PlaylistItem)
        .options(joinedload(PlaylistItem.video))
        .where(PlaylistItem.playlist_id == playlist_id)
        .order_by(PlaylistItem.sort_order)
        .limit(1)
    ).first()
    if first is None:
        raise AppError(code="UNPROCESSABLE", message="プレイリストに動画がありません", status_code=422)

    result = _build_playback_item(db, aid, playlist_id, first, 0)
    upsert_playlist_context(db, aid, playlist_id, first.playlist_item_id, 0)
    db.commit()
    return result


def get_next_playlist_item(
    db: Session, aid: int, playlist_id: int, current_item_id: int
) -> PlaylistNextItemResponse:
    current = _get_item_in_playlist(db, aid, playlist_id, current_item_id)
    nxt = db.scalars(
        select(PlaylistItem)
        .options(joinedload(PlaylistItem.video))
        .where(
            PlaylistItem.playlist_id == playlist_id,
            PlaylistItem.sort_order > current.sort_order,
        )
        .order_by(PlaylistItem.sort_order)
        .limit(1)
    ).first()

    if nxt is None:
        return PlaylistNextItemResponse(has_next=False, item=None)

    item = _build_playback_item(db, aid, playlist_id, nxt, 0)
    upsert_playlist_context(db, aid, playlist_id, nxt.playlist_item_id, 0)
    db.commit()
    return PlaylistNextItemResponse(has_next=True, item=item)


def get_prev_playlist_item(
    db: Session, aid: int, playlist_id: int, current_item_id: int
) -> PlaylistPrevItemResponse:
    current = _get_item_in_playlist(db, aid, playlist_id, current_item_id)
    prev = db.scalars(
        select(PlaylistItem)
        .options(joinedload(PlaylistItem.video))
        .where(
            PlaylistItem.playlist_id == playlist_id,
            PlaylistItem.sort_order < current.sort_order,
        )
        .order_by(PlaylistItem.sort_order.desc())
        .limit(1)
    ).first()

    if prev is None:
        return PlaylistPrevItemResponse(has_prev=False, item=None)

    item = _build_playback_item(db, aid, playlist_id, prev, 0)
    upsert_playlist_context(db, aid, playlist_id, prev.playlist_item_id, 0)
    db.commit()
    return PlaylistPrevItemResponse(has_prev=True, item=item)


def save_playlist_playback_state(
    db: Session,
    aid: int,
    playlist_id: int,
    playlist_item_id: int,
    position_ms: int,
) -> None:
    _get_item_in_playlist(db, aid, playlist_id, playlist_item_id)
    upsert_playlist_context(db, aid, playlist_id, playlist_item_id, position_ms)
    db.commit()
