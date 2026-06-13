from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.database import get_db
from app.dependencies import get_aid_dependency
from app.schemas.series import SeriesCreateRequest, SeriesDetailResponse, SeriesListResponse, SeriesResponse
from app.services import series_service

router = APIRouter(prefix="/series", tags=["series"])


@router.get("", response_model=SeriesListResponse)
def list_series(
    page: int = Query(1, ge=1),
    per_page: int = Query(20, ge=1, le=100),
    q: str | None = Query(None),
    db: Session = Depends(get_db),
    aid: int = Depends(get_aid_dependency()),
) -> SeriesListResponse:
    return series_service.list_series(db, aid, page, per_page, q)


@router.post("", response_model=SeriesResponse, status_code=201)
def create_series(
    body: SeriesCreateRequest,
    db: Session = Depends(get_db),
    aid: int = Depends(get_aid_dependency()),
) -> SeriesResponse:
    return series_service.create_series(db, aid, body)


@router.get("/{series_id}", response_model=SeriesDetailResponse)
def get_series_detail(
    series_id: int,
    db: Session = Depends(get_db),
    aid: int = Depends(get_aid_dependency()),
) -> SeriesDetailResponse:
    return series_service.get_series_detail(db, aid, series_id)
