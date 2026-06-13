from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.dependencies import AppError
from app.models import Series, Video
from app.schemas.series import (
    PaginationMeta,
    SeriesCreateRequest,
    SeriesDetailResponse,
    SeriesListResponse,
    SeriesResponse,
    SeriesVideoBrief,
)
from app.schemas import normalize_page, build_pagination


def list_series(
    db: Session, aid: int, page: int, per_page: int, q: str | None
) -> SeriesListResponse:
    page, per_page, offset = normalize_page(page, per_page)
    base = select(Series).where(Series.aid == aid)
    if q:
        base = base.where(Series.title.ilike(f"%{q}%"))

    count_stmt = select(func.count()).select_from(base.subquery())
    total_count = db.scalar(count_stmt) or 0

    stmt = base.order_by(Series.created_at.desc()).offset(offset).limit(per_page)
    items = [
        SeriesResponse(
            series_id=s.series_id,
            title=s.title,
            description=s.description,
            created_at=s.created_at,
            updated_at=s.updated_at,
        )
        for s in db.scalars(stmt).all()
    ]
    return SeriesListResponse(
        items=items,
        pagination=PaginationMeta(**build_pagination(page, per_page, total_count).model_dump()),
    )


def create_series(db: Session, aid: int, body: SeriesCreateRequest) -> SeriesResponse:
    series = Series(aid=aid, title=body.title, description=body.description)
    db.add(series)
    db.commit()
    db.refresh(series)
    return SeriesResponse(
        series_id=series.series_id,
        title=series.title,
        description=series.description,
        created_at=series.created_at,
        updated_at=series.updated_at,
    )


def get_series_detail(db: Session, aid: int, series_id: int) -> SeriesDetailResponse:
    series = db.get(Series, series_id)
    if series is None or series.aid != aid:
        raise AppError(code="NOT_FOUND", message="作品が見つかりません", status_code=404)

    videos_stmt = (
        select(Video)
        .where(Video.series_id == series_id, Video.aid == aid, Video.status != "deleted")
        .order_by(Video.sort_order, Video.episode_number)
    )
    videos = [
        SeriesVideoBrief(
            video_id=v.video_id,
            episode_number=v.episode_number,
            episode_title=v.episode_title,
            sort_order=v.sort_order,
            duration_ms=v.duration_ms,
            status=v.status,
        )
        for v in db.scalars(videos_stmt).all()
    ]
    return SeriesDetailResponse(
        series_id=series.series_id,
        title=series.title,
        description=series.description,
        videos=videos,
        created_at=series.created_at,
        updated_at=series.updated_at,
    )
