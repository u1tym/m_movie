import re
from collections.abc import Iterator
from dataclasses import dataclass

from sqlalchemy import exists, func, or_, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.dependencies import AppError
from app.models import Genre, PlaybackState, Series, Thumbnail, Video, VideoChunk, VideoGenre
from app.schemas.playback import ChunkMetaResponse
from app.schemas.video import (
    ChunkListResponse,
    ChunkMetaResponse as VideoChunkMeta,
    ChunkUploadResponse,
    GenreBrief,
    PaginationMeta,
    ThumbnailCreateResponse,
    VideoCompleteRequest,
    VideoCompleteResponse,
    VideoCreateRequest,
    VideoCreateResponse,
    VideoDetailResponse,
    VideoListResponse,
    VideoSummaryResponse,
    VideoUpdateRequest,
)
from app.schemas import normalize_page, build_pagination


def _get_owned_video(db: Session, aid: int, video_id: int) -> Video:
    video = db.get(Video, video_id)
    if video is None or video.aid != aid:
        raise AppError(code="NOT_FOUND", message="動画が見つかりません", status_code=404)
    return video


def _validate_genre_ids(db: Session, aid: int, genre_ids: list[int]) -> None:
    if not genre_ids:
        return
    stmt = select(func.count(Genre.genre_id)).where(
        Genre.genre_id.in_(genre_ids),
        or_(Genre.aid.is_(None), Genre.aid == aid),
    )
    count = db.scalar(stmt) or 0
    if count != len(set(genre_ids)):
        raise AppError(code="NOT_FOUND", message="指定されたジャンルが見つかりません", status_code=404)


def _validate_series_id(db: Session, aid: int, series_id: int) -> None:
    series = db.get(Series, series_id)
    if series is None or series.aid != aid:
        raise AppError(code="NOT_FOUND", message="指定された作品が見つかりません", status_code=404)


def _set_video_genres(db: Session, video_id: int, genre_ids: list[int]) -> None:
    db.query(VideoGenre).filter(VideoGenre.video_id == video_id).delete()
    for genre_id in set(genre_ids):
        db.add(VideoGenre(video_id=video_id, genre_id=genre_id))


def _get_genres_for_video(db: Session, video_id: int) -> list[GenreBrief]:
    stmt = (
        select(Genre)
        .join(VideoGenre, VideoGenre.genre_id == Genre.genre_id)
        .where(VideoGenre.video_id == video_id)
        .order_by(Genre.sort_order)
    )
    return [GenreBrief(genre_id=g.genre_id, name=g.name) for g in db.scalars(stmt).all()]


def _get_playback_for_video(db: Session, aid: int, video_id: int) -> PlaybackState | None:
    stmt = select(PlaybackState).where(
        PlaybackState.aid == aid, PlaybackState.video_id == video_id
    )
    return db.scalars(stmt).first()


def _to_summary(
    db: Session,
    aid: int,
    video: Video,
    series_title: str | None = None,
) -> VideoSummaryResponse:
    playback = _get_playback_for_video(db, aid, video.video_id)
    has_thumb = db.scalar(
        select(exists().where(Thumbnail.video_id == video.video_id))
    )
    return VideoSummaryResponse(
        video_id=video.video_id,
        title=video.title,
        description=video.description,
        series_id=video.series_id,
        series_title=series_title,
        episode_number=video.episode_number,
        episode_title=video.episode_title,
        sort_order=video.sort_order,
        duration_ms=video.duration_ms,
        mime_type=video.mime_type,
        file_size_bytes=video.file_size_bytes,
        status=video.status,
        genres=_get_genres_for_video(db, video.video_id),
        has_thumbnail=bool(has_thumb),
        position_ms=playback.position_ms if playback else None,
        completed=playback.completed if playback else False,
        created_at=video.created_at,
        updated_at=video.updated_at,
    )


def list_videos(
    db: Session,
    aid: int,
    page: int,
    per_page: int,
    genre_id: int | None,
    series_id: int | None,
    status: str | None,
    q: str | None,
    sort: str,
    order: str,
) -> VideoListResponse:
    page, per_page, offset = normalize_page(page, per_page)
    stmt = select(Video).where(Video.aid == aid)

    if status == "all":
        pass
    elif status:
        stmt = stmt.where(Video.status == status)
    else:
        stmt = stmt.where(Video.status == "ready")

    if genre_id is not None:
        stmt = stmt.join(VideoGenre, VideoGenre.video_id == Video.video_id).where(
            VideoGenre.genre_id == genre_id
        )
    if series_id is not None:
        stmt = stmt.where(Video.series_id == series_id)
    if q:
        stmt = stmt.where(
            or_(Video.title.ilike(f"%{q}%"), Video.episode_title.ilike(f"%{q}%"))
        )

    count_stmt = select(func.count()).select_from(stmt.subquery())
    total_count = db.scalar(count_stmt) or 0

    sort_col = Video.created_at
    if sort == "title":
        sort_col = Video.title
    elif sort == "last_played_at":
        stmt = stmt.outerjoin(
            PlaybackState,
            (PlaybackState.video_id == Video.video_id) & (PlaybackState.aid == aid),
        )
        sort_col = PlaybackState.last_played_at

    if order == "asc":
        stmt = stmt.order_by(sort_col.asc().nulls_last())
    else:
        stmt = stmt.order_by(sort_col.desc().nulls_last())

    videos = db.scalars(stmt.offset(offset).limit(per_page)).all()

    series_titles: dict[int, str] = {}
    series_ids = {v.series_id for v in videos if v.series_id is not None}
    if series_ids:
        series_rows = db.scalars(select(Series).where(Series.series_id.in_(series_ids))).all()
        series_titles = {s.series_id: s.title for s in series_rows}

    items = [
        _to_summary(
            db,
            aid,
            v,
            series_titles.get(v.series_id) if v.series_id else None,
        )
        for v in videos
    ]
    return VideoListResponse(
        items=items,
        pagination=PaginationMeta(**build_pagination(page, per_page, total_count).model_dump()),
    )


def get_video_detail(db: Session, aid: int, video_id: int) -> VideoDetailResponse:
    video = _get_owned_video(db, aid, video_id)
    if video.status == "deleted":
        raise AppError(code="NOT_FOUND", message="動画が見つかりません", status_code=404)

    series_title = None
    if video.series_id:
        series = db.get(Series, video.series_id)
        series_title = series.title if series else None

    playback = _get_playback_for_video(db, aid, video_id)
    summary = _to_summary(db, aid, video, series_title)
    return VideoDetailResponse(
        **summary.model_dump(),
        chunk_count=video.chunk_count,
        last_played_at=playback.last_played_at if playback else None,
        play_count=playback.play_count if playback else 0,
    )


def create_video(db: Session, aid: int, body: VideoCreateRequest) -> VideoCreateResponse:
    if body.series_id is not None:
        _validate_series_id(db, aid, body.series_id)
    _validate_genre_ids(db, aid, body.genre_ids)

    video = Video(
        aid=aid,
        title=body.title,
        description=body.description,
        series_id=body.series_id,
        episode_number=body.episode_number,
        episode_title=body.episode_title,
        sort_order=body.sort_order,
        duration_ms=body.duration_ms,
        mime_type=body.mime_type,
        status="uploading",
    )
    db.add(video)
    try:
        db.flush()
        if body.genre_ids:
            _set_video_genres(db, video.video_id, body.genre_ids)
        db.commit()
    except IntegrityError as exc:
        db.rollback()
        raise AppError(
            code="CONFLICT",
            message="同一作品内で話数が重複しています",
            status_code=409,
        ) from exc
    db.refresh(video)
    return VideoCreateResponse(
        video_id=video.video_id,
        status=video.status,
        title=video.title,
        chunk_count=video.chunk_count,
        created_at=video.created_at,
    )


def update_video(db: Session, aid: int, video_id: int, body: VideoUpdateRequest) -> VideoDetailResponse:
    video = _get_owned_video(db, aid, video_id)
    if video.status == "deleted":
        raise AppError(code="NOT_FOUND", message="動画が見つかりません", status_code=404)

    data = body.model_dump(exclude_unset=True)
    genre_ids = data.pop("genre_ids", None)

    if "series_id" in data and data["series_id"] is not None:
        _validate_series_id(db, aid, data["series_id"])

    for key, value in data.items():
        setattr(video, key, value)

    if genre_ids is not None:
        _validate_genre_ids(db, aid, genre_ids)
        _set_video_genres(db, video.video_id, genre_ids)

    try:
        db.commit()
    except IntegrityError as exc:
        db.rollback()
        raise AppError(
            code="CONFLICT",
            message="同一作品内で話数が重複しています",
            status_code=409,
        ) from exc
    db.refresh(video)
    return get_video_detail(db, aid, video_id)


def delete_video(db: Session, aid: int, video_id: int) -> None:
    video = _get_owned_video(db, aid, video_id)
    db.delete(video)
    db.commit()


def upload_chunk(
    db: Session,
    aid: int,
    video_id: int,
    chunk_index: int,
    start_time_ms: int,
    end_time_ms: int,
    data: bytes,
) -> ChunkUploadResponse:
    if chunk_index < 0:
        raise AppError(code="VALIDATION_ERROR", message="chunk_index は 0 以上である必要があります", status_code=400)
    if start_time_ms < 0 or end_time_ms <= start_time_ms:
        raise AppError(code="VALIDATION_ERROR", message="時刻範囲が不正です", status_code=400)
    if not data:
        raise AppError(code="VALIDATION_ERROR", message="チャンクデータが空です", status_code=400)

    video = _get_owned_video(db, aid, video_id)
    if video.status != "uploading":
        raise AppError(
            code="UNPROCESSABLE",
            message="アップロード中の動画のみチャンクを追加できます",
            status_code=422,
        )

    existing = db.scalars(
        select(VideoChunk).where(
            VideoChunk.video_id == video_id, VideoChunk.chunk_index == chunk_index
        )
    ).first()
    if existing:
        raise AppError(code="CONFLICT", message="同一 chunk_index が既に登録されています", status_code=409)

    byte_length = len(data)
    chunk = VideoChunk(
        video_id=video_id,
        chunk_index=chunk_index,
        start_time_ms=start_time_ms,
        end_time_ms=end_time_ms,
        byte_length=byte_length,
        data=data,
    )
    db.add(chunk)
    video.chunk_count += 1
    video.file_size_bytes += byte_length
    db.commit()
    db.refresh(video)
    return ChunkUploadResponse(
        video_id=video_id,
        chunk_index=chunk_index,
        byte_length=byte_length,
        uploaded_chunks=video.chunk_count,
    )


def complete_upload(
    db: Session, aid: int, video_id: int, body: VideoCompleteRequest
) -> VideoCompleteResponse:
    video = _get_owned_video(db, aid, video_id)
    if video.status != "uploading":
        raise AppError(
            code="UNPROCESSABLE",
            message="アップロード中の動画のみ完了処理が可能です",
            status_code=422,
        )
    if video.chunk_count == 0:
        raise AppError(code="UNPROCESSABLE", message="チャンクが登録されていません", status_code=422)
    if video.chunk_count != body.chunk_count:
        raise AppError(
            code="UNPROCESSABLE",
            message="チャンク数が一致しません",
            status_code=422,
        )

    video.duration_ms = body.duration_ms
    video.status = "ready"
    db.commit()
    db.refresh(video)
    return VideoCompleteResponse(
        video_id=video.video_id,
        status=video.status,
        duration_ms=video.duration_ms,
        chunk_count=video.chunk_count,
        file_size_bytes=video.file_size_bytes,
    )


def list_chunk_meta(db: Session, aid: int, video_id: int) -> ChunkListResponse:
    video = _get_owned_video(db, aid, video_id)
    stmt = (
        select(VideoChunk)
        .where(VideoChunk.video_id == video_id)
        .order_by(VideoChunk.chunk_index)
    )
    items = [
        VideoChunkMeta(
            chunk_index=c.chunk_index,
            start_time_ms=c.start_time_ms,
            end_time_ms=c.end_time_ms,
            byte_length=c.byte_length,
        )
        for c in db.scalars(stmt).all()
    ]
    return ChunkListResponse(video_id=video_id, chunk_count=video.chunk_count, items=items)


def get_chunk_data(db: Session, aid: int, video_id: int, chunk_index: int) -> tuple[Video, VideoChunk]:
    video = _get_owned_video(db, aid, video_id)
    if video.status != "ready":
        raise AppError(
            code="UNPROCESSABLE",
            message="再生可能な動画ではありません",
            status_code=422,
        )
    chunk = db.scalars(
        select(VideoChunk).where(
            VideoChunk.video_id == video_id, VideoChunk.chunk_index == chunk_index
        )
    ).first()
    if chunk is None:
        raise AppError(code="NOT_FOUND", message="チャンクが見つかりません", status_code=404)
    return video, chunk


def find_chunk_at_position(db: Session, video_id: int, position_ms: int) -> VideoChunk:
    chunk = db.scalars(
        select(VideoChunk)
        .where(VideoChunk.video_id == video_id, VideoChunk.start_time_ms <= position_ms)
        .order_by(VideoChunk.start_time_ms.desc())
        .limit(1)
    ).first()
    if chunk is None:
        chunk = db.scalars(
            select(VideoChunk)
            .where(VideoChunk.video_id == video_id)
            .order_by(VideoChunk.chunk_index)
            .limit(1)
        ).first()
    if chunk is None:
        raise AppError(code="NOT_FOUND", message="チャンクが見つかりません", status_code=404)
    return chunk


def chunk_to_meta(chunk: VideoChunk) -> ChunkMetaResponse:
    return ChunkMetaResponse(
        chunk_index=chunk.chunk_index,
        start_time_ms=chunk.start_time_ms,
        end_time_ms=chunk.end_time_ms,
        byte_length=chunk.byte_length,
    )


def upsert_thumbnail(
    db: Session,
    aid: int,
    video_id: int,
    data: bytes,
    mime_type: str,
    width: int | None,
    height: int | None,
) -> ThumbnailCreateResponse:
    if not data:
        raise AppError(code="VALIDATION_ERROR", message="画像データが空です", status_code=400)

    video = _get_owned_video(db, aid, video_id)
    existing = db.scalars(select(Thumbnail).where(Thumbnail.video_id == video_id)).first()
    if existing:
        existing.data = data
        existing.mime_type = mime_type
        existing.width = width
        existing.height = height
        thumb = existing
    else:
        thumb = Thumbnail(
            video_id=video_id,
            data=data,
            mime_type=mime_type,
            width=width,
            height=height,
        )
        db.add(thumb)
    db.commit()
    return ThumbnailCreateResponse(
        video_id=video.video_id,
        mime_type=thumb.mime_type,
        width=thumb.width,
        height=thumb.height,
    )


def get_thumbnail(db: Session, aid: int, video_id: int) -> Thumbnail:
    _get_owned_video(db, aid, video_id)
    thumb = db.scalars(select(Thumbnail).where(Thumbnail.video_id == video_id)).first()
    if thumb is None:
        raise AppError(code="NOT_FOUND", message="サムネイルが見つかりません", status_code=404)
    return thumb


_RANGE_RE = re.compile(r"^bytes=(\d+)-(\d*)$")


@dataclass
class VideoStreamResult:
    status_code: int
    media_type: str
    content_length: int
    content_range: str | None
    body: Iterator[bytes]


def _ordered_chunks(db: Session, video_id: int) -> list[VideoChunk]:
    return list(
        db.scalars(
            select(VideoChunk)
            .where(VideoChunk.video_id == video_id)
            .order_by(VideoChunk.chunk_index)
        ).all()
    )


def _build_chunk_offsets(chunks: list[VideoChunk]) -> list[tuple[VideoChunk, int, int]]:
    result: list[tuple[VideoChunk, int, int]] = []
    offset = 0
    for chunk in chunks:
        result.append((chunk, offset, offset + chunk.byte_length))
        offset += chunk.byte_length
    return result


def _iter_byte_range(
    chunk_offsets: list[tuple[VideoChunk, int, int]],
    start: int,
    end: int,
) -> Iterator[bytes]:
    for chunk, chunk_start, chunk_end in chunk_offsets:
        if chunk_end <= start:
            continue
        if chunk_start > end:
            break
        local_start = start - chunk_start
        local_end = min(chunk.byte_length, end - chunk_start + 1)
        yield chunk.data[local_start:local_end]


def stream_video(
    db: Session,
    aid: int,
    video_id: int,
    range_header: str | None,
) -> VideoStreamResult:
    video = _get_owned_video(db, aid, video_id)
    if video.status != "ready":
        raise AppError(
            code="UNPROCESSABLE",
            message="再生可能な動画ではありません",
            status_code=422,
        )
    if video.file_size_bytes <= 0:
        raise AppError(
            code="UNPROCESSABLE",
            message="再生可能なデータがありません",
            status_code=422,
        )

    chunks = _ordered_chunks(db, video_id)
    if not chunks:
        raise AppError(code="NOT_FOUND", message="チャンクが見つかりません", status_code=404)

    total = video.file_size_bytes
    chunk_offsets = _build_chunk_offsets(chunks)

    if range_header:
        match = _RANGE_RE.match(range_header.strip())
        if not match:
            raise AppError(
                code="VALIDATION_ERROR",
                message="Range ヘッダーが不正です",
                status_code=400,
            )
        start = int(match.group(1))
        end = int(match.group(2)) if match.group(2) else total - 1
        if start >= total or start > end:
            raise AppError(
                code="RANGE_NOT_SATISFIABLE",
                message="要求された Range は満たせません",
                status_code=416,
            )
        end = min(end, total - 1)
        length = end - start + 1
        return VideoStreamResult(
            status_code=206,
            media_type=video.mime_type,
            content_length=length,
            content_range=f"bytes {start}-{end}/{total}",
            body=_iter_byte_range(chunk_offsets, start, end),
        )

    return VideoStreamResult(
        status_code=200,
        media_type=video.mime_type,
        content_length=total,
        content_range=None,
        body=_iter_byte_range(chunk_offsets, 0, total - 1),
    )
