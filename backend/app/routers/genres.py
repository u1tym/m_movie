from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.database import get_db
from app.dependencies import get_aid_dependency
from app.schemas.genre import GenreCreateRequest, GenreListResponse, GenreResponse
from app.services import genre_service

router = APIRouter(prefix="/genres", tags=["genres"])


@router.get("", response_model=GenreListResponse)
def list_genres(
    db: Session = Depends(get_db),
    aid: int = Depends(get_aid_dependency()),
) -> GenreListResponse:
    return GenreListResponse(items=genre_service.list_genres(db, aid))


@router.post("", response_model=GenreResponse, status_code=201)
def create_genre(
    body: GenreCreateRequest,
    db: Session = Depends(get_db),
    aid: int = Depends(get_aid_dependency()),
) -> GenreResponse:
    return genre_service.create_genre(db, aid, body)
