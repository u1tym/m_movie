from contextlib import asynccontextmanager
import logging

from fastapi import FastAPI
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from starlette.exceptions import HTTPException as StarletteHTTPException

from app.config import settings
from app.dependencies import app_error_handler, http_exception_handler, validation_exception_handler, AppError
from app.routers import genres, playback, series, videos

logger = logging.getLogger("uvicorn.error")


@asynccontextmanager
async def lifespan(_app: FastAPI):
    from app.config import loaded_env_file

    logger.info(
        "Movie API started: DEBUG=%s, DEBUG_AID=%s, env_file=%s",
        settings.debug,
        settings.debug_aid,
        loaded_env_file or "(none — cwd/.env not found)",
    )
    yield


app = FastAPI(title="Movie API", version="1.0.0", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origin_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.add_exception_handler(AppError, app_error_handler)
app.add_exception_handler(StarletteHTTPException, http_exception_handler)
app.add_exception_handler(RequestValidationError, validation_exception_handler)

API_PREFIX = "/api/v1/movie"
app.include_router(genres.router, prefix=API_PREFIX)
app.include_router(series.router, prefix=API_PREFIX)
app.include_router(videos.router, prefix=API_PREFIX)
app.include_router(playback.router, prefix=API_PREFIX)


@app.get("/health")
def health() -> dict[str, str | bool | int]:
    return {
        "status": "ok",
        "debug": settings.debug,
        "debug_aid": settings.debug_aid,
    }
