from datetime import datetime, timezone

from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.orm import Session

from app.models import PlaybackContext


def _get_or_create_context(db: Session, aid: int) -> PlaybackContext:
    ctx = db.get(PlaybackContext, aid)
    if ctx is None:
        ctx = PlaybackContext(aid=aid)
        db.add(ctx)
        db.flush()
    return ctx


def update_video_context(db: Session, aid: int, video_id: int, position_ms: int) -> None:
    now = datetime.now(timezone.utc)
    ctx = _get_or_create_context(db, aid)
    ctx.last_video_id = video_id
    ctx.last_video_position_ms = position_ms
    ctx.last_video_updated_at = now
    ctx.updated_at = now


def update_playlist_context(
    db: Session,
    aid: int,
    playlist_id: int,
    playlist_item_id: int,
    position_ms: int,
) -> None:
    now = datetime.now(timezone.utc)
    ctx = _get_or_create_context(db, aid)
    ctx.last_playlist_id = playlist_id
    ctx.last_playlist_item_id = playlist_item_id
    ctx.last_playlist_position_ms = position_ms
    ctx.last_playlist_updated_at = now
    ctx.updated_at = now


def upsert_video_context(db: Session, aid: int, video_id: int, position_ms: int) -> None:
    now = datetime.now(timezone.utc)
    stmt = (
        insert(PlaybackContext)
        .values(
            aid=aid,
            last_video_id=video_id,
            last_video_position_ms=position_ms,
            last_video_updated_at=now,
            last_playlist_position_ms=0,
            updated_at=now,
        )
        .on_conflict_do_update(
            index_elements=["aid"],
            set_={
                "last_video_id": video_id,
                "last_video_position_ms": position_ms,
                "last_video_updated_at": now,
                "updated_at": now,
            },
        )
    )
    db.execute(stmt)


def upsert_playlist_context(
    db: Session,
    aid: int,
    playlist_id: int,
    playlist_item_id: int,
    position_ms: int,
) -> None:
    now = datetime.now(timezone.utc)
    stmt = (
        insert(PlaybackContext)
        .values(
            aid=aid,
            last_playlist_id=playlist_id,
            last_playlist_item_id=playlist_item_id,
            last_playlist_position_ms=position_ms,
            last_playlist_updated_at=now,
            last_video_position_ms=0,
            updated_at=now,
        )
        .on_conflict_do_update(
            index_elements=["aid"],
            set_={
                "last_playlist_id": playlist_id,
                "last_playlist_item_id": playlist_item_id,
                "last_playlist_position_ms": position_ms,
                "last_playlist_updated_at": now,
                "updated_at": now,
            },
        )
    )
    db.execute(stmt)
