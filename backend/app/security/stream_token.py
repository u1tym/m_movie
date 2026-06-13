from datetime import datetime, timedelta, timezone

import jwt
from fastapi import HTTPException

from app.config import settings

PURPOSE = "video_stream"


def create_stream_token(aid: int, video_id: int, expires_minutes: int = 120) -> str:
    payload = {
        "sub": str(aid),
        "video_id": video_id,
        "purpose": PURPOSE,
        "exp": datetime.now(timezone.utc) + timedelta(minutes=expires_minutes),
    }
    return jwt.encode(payload, settings.secret_key, algorithm=settings.algorithm)


def verify_stream_token(token: str, video_id: int) -> int:
    try:
        payload = jwt.decode(
            token,
            settings.secret_key,
            algorithms=[settings.algorithm],
        )
    except jwt.PyJWTError as exc:
        raise HTTPException(status_code=401, detail="ストリームトークンが無効です") from exc

    if payload.get("purpose") != PURPOSE:
        raise HTTPException(status_code=401, detail="ストリームトークンが無効です")
    if payload.get("video_id") != video_id:
        raise HTTPException(status_code=403, detail="この動画へのアクセス権がありません")

    sub = payload.get("sub")
    if sub is None:
        raise HTTPException(status_code=401, detail="ストリームトークンが無効です")
    try:
        return int(str(sub))
    except ValueError as exc:
        raise HTTPException(status_code=401, detail="ストリームトークンが無効です") from exc
