from sqlalchemy import or_, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.dependencies import AppError
from app.models import Genre
from app.schemas.genre import GenreCreateRequest, GenreResponse


def list_genres(db: Session, aid: int) -> list[GenreResponse]:
    stmt = (
        select(Genre)
        .where(or_(Genre.aid.is_(None), Genre.aid == aid))
        .order_by(Genre.sort_order, Genre.genre_id)
    )
    genres = db.scalars(stmt).all()
    return [
        GenreResponse(
            genre_id=g.genre_id,
            name=g.name,
            sort_order=g.sort_order,
            is_system=g.aid is None,
        )
        for g in genres
    ]


def create_genre(db: Session, aid: int, body: GenreCreateRequest) -> GenreResponse:
    genre = Genre(aid=aid, name=body.name, sort_order=body.sort_order)
    db.add(genre)
    try:
        db.commit()
    except IntegrityError as exc:
        db.rollback()
        raise AppError(
            code="CONFLICT",
            message="同名のジャンルが既に存在します",
            status_code=409,
        ) from exc
    db.refresh(genre)
    return GenreResponse(
        genre_id=genre.genre_id,
        name=genre.name,
        sort_order=genre.sort_order,
        is_system=False,
    )
