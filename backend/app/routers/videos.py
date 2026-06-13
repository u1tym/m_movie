from fastapi import APIRouter, Depends, File, Form, Query, Request, UploadFile
from fastapi.responses import Response, StreamingResponse
from sqlalchemy.orm import Session

from app.config import settings
from app.database import get_db
from app.dependencies import get_aid_dependency, get_current_aid
from app.security.stream_token import verify_stream_token
from app.schemas.video import (
    ChunkListResponse,
    ChunkUploadResponse,
    ThumbnailCreateResponse,
    VideoCompleteRequest,
    VideoCompleteResponse,
    VideoCreateRequest,
    VideoCreateResponse,
    VideoDetailResponse,
    VideoListResponse,
    VideoUpdateRequest,
)
from app.services import video_service

router = APIRouter(prefix="/videos", tags=["videos"])


def _get_stream_aid(video_id: int, request: Request, token: str | None = Query(None)) -> int:
    if settings.debug:
        return settings.debug_aid
    if token:
        return verify_stream_token(token, video_id)
    return get_current_aid(request)


@router.get("", response_model=VideoListResponse)
def list_videos(
    page: int = Query(1, ge=1),
    per_page: int = Query(20, ge=1, le=100),
    genre_id: int | None = Query(None),
    series_id: int | None = Query(None),
    status: str | None = Query(None),
    q: str | None = Query(None),
    sort: str = Query("created_at"),
    order: str = Query("desc"),
    db: Session = Depends(get_db),
    aid: int = Depends(get_aid_dependency()),
) -> VideoListResponse:
    return video_service.list_videos(
        db, aid, page, per_page, genre_id, series_id, status, q, sort, order
    )


@router.post("", response_model=VideoCreateResponse, status_code=201)
def create_video(
    body: VideoCreateRequest,
    db: Session = Depends(get_db),
    aid: int = Depends(get_aid_dependency()),
) -> VideoCreateResponse:
    return video_service.create_video(db, aid, body)


@router.get("/{video_id}", response_model=VideoDetailResponse)
def get_video(
    video_id: int,
    db: Session = Depends(get_db),
    aid: int = Depends(get_aid_dependency()),
) -> VideoDetailResponse:
    return video_service.get_video_detail(db, aid, video_id)


@router.put("/{video_id}", response_model=VideoDetailResponse)
def update_video(
    video_id: int,
    body: VideoUpdateRequest,
    db: Session = Depends(get_db),
    aid: int = Depends(get_aid_dependency()),
) -> VideoDetailResponse:
    return video_service.update_video(db, aid, video_id, body)


@router.delete("/{video_id}", status_code=204)
def delete_video(
    video_id: int,
    db: Session = Depends(get_db),
    aid: int = Depends(get_aid_dependency()),
) -> None:
    video_service.delete_video(db, aid, video_id)


@router.post("/{video_id}/chunks", response_model=ChunkUploadResponse, status_code=201)
async def upload_chunk(
    video_id: int,
    chunk_index: int = Form(...),
    start_time_ms: int = Form(...),
    end_time_ms: int = Form(...),
    data: UploadFile = File(...),
    db: Session = Depends(get_db),
    aid: int = Depends(get_aid_dependency()),
) -> ChunkUploadResponse:
    content = await data.read()
    return video_service.upload_chunk(
        db, aid, video_id, chunk_index, start_time_ms, end_time_ms, content
    )


@router.post("/{video_id}/complete", response_model=VideoCompleteResponse)
def complete_upload(
    video_id: int,
    body: VideoCompleteRequest,
    db: Session = Depends(get_db),
    aid: int = Depends(get_aid_dependency()),
) -> VideoCompleteResponse:
    return video_service.complete_upload(db, aid, video_id, body)


@router.get("/{video_id}/stream")
def stream_video(
    video_id: int,
    request: Request,
    token: str | None = Query(None),
    db: Session = Depends(get_db),
    aid: int = Depends(_get_stream_aid),
) -> StreamingResponse:
    result = video_service.stream_video(db, aid, video_id, request.headers.get("range"))
    headers = {
        "Accept-Ranges": "bytes",
        "Content-Length": str(result.content_length),
        "Access-Control-Expose-Headers": "Content-Range, Accept-Ranges, Content-Length",
    }
    if result.content_range:
        headers["Content-Range"] = result.content_range
    return StreamingResponse(
        result.body,
        status_code=result.status_code,
        media_type=result.media_type,
        headers=headers,
    )


@router.get("/{video_id}/chunks", response_model=ChunkListResponse)
def list_chunks(
    video_id: int,
    db: Session = Depends(get_db),
    aid: int = Depends(get_aid_dependency()),
) -> ChunkListResponse:
    return video_service.list_chunk_meta(db, aid, video_id)


@router.get("/{video_id}/chunks/{chunk_index}")
def get_chunk(
    video_id: int,
    chunk_index: int,
    db: Session = Depends(get_db),
    aid: int = Depends(get_aid_dependency()),
) -> Response:
    video, chunk = video_service.get_chunk_data(db, aid, video_id, chunk_index)
    return Response(
        content=chunk.data,
        media_type=video.mime_type,
        headers={
            "X-Chunk-Index": str(chunk.chunk_index),
            "X-Start-Time-Ms": str(chunk.start_time_ms),
            "X-End-Time-Ms": str(chunk.end_time_ms),
        },
    )


@router.get("/{video_id}/thumbnail")
def get_thumbnail(
    video_id: int,
    db: Session = Depends(get_db),
    aid: int = Depends(get_aid_dependency()),
) -> Response:
    thumb = video_service.get_thumbnail(db, aid, video_id)
    return Response(content=thumb.data, media_type=thumb.mime_type)


@router.post("/{video_id}/thumbnail", response_model=ThumbnailCreateResponse, status_code=201)
async def upload_thumbnail(
    video_id: int,
    data: UploadFile = File(...),
    mime_type: str = Form("image/jpeg"),
    width: int | None = Form(None),
    height: int | None = Form(None),
    db: Session = Depends(get_db),
    aid: int = Depends(get_aid_dependency()),
) -> ThumbnailCreateResponse:
    content = await data.read()
    return video_service.upsert_thumbnail(db, aid, video_id, content, mime_type, width, height)
