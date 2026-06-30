from datetime import datetime, timezone

from sqlalchemy import func, select
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.orm import Session, joinedload

from app.dependencies import AppError
from app.models import PlaybackState, Video
from app.schemas.playback import (
    ChunkMetaResponse,
    HistoryItemResponse,
    HistoryListResponse,
    NextVideoBrief,
    NextVideoResponse,
    PaginationMeta,
    PlaybackSeekResponse,
    PlaybackStartRequest,
    PlaybackStartResponse,
    PlaybackStateResponse,
    PlaybackStateUpdateRequest,
)
from app.schemas import normalize_page, build_pagination
from app.services.playback_context_service import upsert_playlist_context, upsert_video_context
from app.services.video_service import (
    _get_owned_video,
    chunk_to_meta,
    find_chunk_at_position,
)


def _get_or_create_playback(db: Session, aid: int, video_id: int) -> PlaybackState:
    playback = db.scalars(
        select(PlaybackState).where(
            PlaybackState.aid == aid, PlaybackState.video_id == video_id
        )
    ).first()
    if playback is None:
        playback = PlaybackState(aid=aid, video_id=video_id)
        db.add(playback)
        db.flush()
    return playback


def start_playback(
    db: Session, aid: int, video_id: int, body: PlaybackStartRequest
) -> PlaybackStartResponse:
    video = _get_owned_video(db, aid, video_id)
    if video.status != "ready":
        raise AppError(
            code="UNPROCESSABLE",
            message="再生可能な動画ではありません",
            status_code=422,
        )

    playback = _get_or_create_playback(db, aid, video_id)
    position_ms = playback.position_ms if body.resume else 0
    if position_ms > video.duration_ms:
        position_ms = 0

    chunk = find_chunk_at_position(db, video_id, position_ms)
    now = datetime.now(timezone.utc)
    playback.play_count += 1
    playback.last_played_at = now
    playback.updated_at = now
    upsert_video_context(db, aid, video_id, position_ms)
    db.commit()

    return PlaybackStartResponse(
        video_id=video.video_id,
        title=video.title,
        duration_ms=video.duration_ms,
        mime_type=video.mime_type,
        chunk_count=video.chunk_count,
        position_ms=position_ms,
        completed=playback.completed,
        status=video.status,
        start_chunk=chunk_to_meta(chunk),
        stream_token=create_stream_token(aid, video.video_id),
    )


def seek_playback(
    db: Session, aid: int, video_id: int, position_ms: int, base_path: str
) -> PlaybackSeekResponse:
    video = _get_owned_video(db, aid, video_id)
    if video.status != "ready":
        raise AppError(
            code="UNPROCESSABLE",
            message="再生可能な動画ではありません",
            status_code=422,
        )
    if position_ms < 0 or position_ms > video.duration_ms:
        raise AppError(
            code="VALIDATION_ERROR",
            message="再生位置が動画の範囲外です",
            status_code=400,
        )

    chunk = find_chunk_at_position(db, video_id, position_ms)
    return PlaybackSeekResponse(
        video_id=video_id,
        position_ms=position_ms,
        chunk=ChunkMetaResponse(
            chunk_index=chunk.chunk_index,
            start_time_ms=chunk.start_time_ms,
            end_time_ms=chunk.end_time_ms,
            byte_length=chunk.byte_length,
        ),
        chunk_url=f"{base_path}/videos/{video_id}/chunks/{chunk.chunk_index}",
    )


def get_playback_state(db: Session, aid: int, video_id: int) -> PlaybackStateResponse:
    _get_owned_video(db, aid, video_id)
    playback = db.scalars(
        select(PlaybackState).where(
            PlaybackState.aid == aid, PlaybackState.video_id == video_id
        )
    ).first()
    if playback is None:
        return PlaybackStateResponse(
            video_id=video_id,
            position_ms=0,
            completed=False,
            play_count=0,
            last_played_at=None,
        )
    return PlaybackStateResponse(
        video_id=video_id,
        position_ms=playback.position_ms,
        completed=playback.completed,
        play_count=playback.play_count,
        last_played_at=playback.last_played_at,
    )


def update_playback_state(
    db: Session, aid: int, video_id: int, body: PlaybackStateUpdateRequest
) -> PlaybackStateResponse:
    video = _get_owned_video(db, aid, video_id)
    if body.position_ms > video.duration_ms:
        raise AppError(
            code="VALIDATION_ERROR",
            message="再生位置が動画の範囲外です",
            status_code=400,
        )

    now = datetime.now(timezone.utc)
    completed = body.completed if body.completed is not None else False
    stmt = (
        insert(PlaybackState)
        .values(
            aid=aid,
            video_id=video_id,
            position_ms=body.position_ms,
            completed=completed,
            play_count=0,
            last_played_at=now,
            updated_at=now,
        )
        .on_conflict_do_update(
            index_elements=["aid", "video_id"],
            set_={
                "position_ms": body.position_ms,
                "completed": completed,
                "last_played_at": now,
                "updated_at": now,
            },
        )
    )
    db.execute(stmt)
    if body.playlist_id is not None and body.playlist_item_id is not None:
        upsert_playlist_context(
            db, aid, body.playlist_id, body.playlist_item_id, body.position_ms
        )
    else:
        upsert_video_context(db, aid, video_id, body.position_ms)
    db.commit()
    return get_playback_state(db, aid, video_id)


def get_next_video(db: Session, aid: int, video_id: int) -> NextVideoResponse:
    current = _get_owned_video(db, aid, video_id)

    if current.series_id is not None:
        stmt = (
            select(Video)
            .where(
                Video.series_id == current.series_id,
                Video.aid == aid,
                Video.status == "ready",
                Video.sort_order > current.sort_order,
            )
            .order_by(Video.sort_order.asc())
            .limit(1)
        )
    else:
        stmt = (
            select(Video)
            .where(
                Video.aid == aid,
                Video.status == "ready",
                Video.series_id.is_(None),
                Video.created_at > current.created_at,
            )
            .order_by(Video.created_at.asc())
            .limit(1)
        )

    nxt = db.scalars(stmt).first()
    if nxt is None:
        return NextVideoResponse(has_next=False, video=None)

    return NextVideoResponse(
        has_next=True,
        video=NextVideoBrief(
            video_id=nxt.video_id,
            title=nxt.title,
            episode_number=nxt.episode_number,
            sort_order=nxt.sort_order,
            duration_ms=nxt.duration_ms,
            status=nxt.status,
        ),
    )


def list_history(db: Session, aid: int, page: int, per_page: int) -> HistoryListResponse:
    page, per_page, offset = normalize_page(page, per_page)
    base = (
        select(PlaybackState, Video)
        .join(Video, Video.video_id == PlaybackState.video_id)
        .where(PlaybackState.aid == aid, Video.status != "deleted")
    )
    count_stmt = select(func.count()).select_from(base.subquery())
    total_count = db.scalar(count_stmt) or 0

    stmt = base.order_by(PlaybackState.last_played_at.desc()).offset(offset).limit(per_page)
    items = [
        HistoryItemResponse(
            video_id=video.video_id,
            title=video.title,
            position_ms=playback.position_ms,
            completed=playback.completed,
            duration_ms=video.duration_ms,
            last_played_at=playback.last_played_at,
        )
        for playback, video in db.execute(stmt).all()
    ]
    return HistoryListResponse(
        items=items,
        pagination=PaginationMeta(**build_pagination(page, per_page, total_count).model_dump()),
    )


def get_last_playback(db: Session, aid: int):
    from app.models import PlaybackContext
    from app.schemas.playback_context import (
        LastPlaybackResponse,
        LastPlaylistContextResponse,
        LastVideoContextResponse,
    )

    ctx = db.get(PlaybackContext, aid)
    if ctx is None:
        return LastPlaybackResponse()

    video_ctx = None
    if ctx.last_video_id is not None and ctx.last_video_updated_at is not None:
        video = db.get(Video, ctx.last_video_id)
        if video is not None and video.aid == aid and video.status == "ready":
            video_ctx = LastVideoContextResponse(
                video_id=video.video_id,
                title=video.title,
                duration_ms=video.duration_ms,
                position_ms=ctx.last_video_position_ms,
                updated_at=ctx.last_video_updated_at,
            )

    playlist_ctx = None
    if (
        ctx.last_playlist_id is not None
        and ctx.last_playlist_item_id is not None
        and ctx.last_playlist_updated_at is not None
    ):
        from app.models import Playlist, PlaylistItem

        playlist = db.get(Playlist, ctx.last_playlist_id)
        item = db.scalars(
            select(PlaylistItem)
            .options(joinedload(PlaylistItem.video))
            .where(PlaylistItem.playlist_item_id == ctx.last_playlist_item_id)
        ).first()
        if (
            playlist is not None
            and playlist.aid == aid
            and item is not None
            and item.video.status == "ready"
        ):
            playlist_ctx = LastPlaylistContextResponse(
                playlist_id=playlist.playlist_id,
                playlist_name=playlist.name,
                playlist_item_id=item.playlist_item_id,
                video_id=item.video_id,
                video_title=item.video.title,
                duration_ms=item.video.duration_ms,
                position_ms=ctx.last_playlist_position_ms,
                updated_at=ctx.last_playlist_updated_at,
            )

    return LastPlaybackResponse(video=video_ctx, playlist=playlist_ctx)
