from fastapi import HTTPException, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from starlette.exceptions import HTTPException as StarletteHTTPException

from app.config import settings
from app.security.jwt_verifier import JWTVerifier


class AppError(Exception):
    def __init__(
        self,
        code: str,
        message: str,
        status_code: int = 400,
        details: list[dict[str, str]] | None = None,
    ) -> None:
        self.code = code
        self.message = message
        self.status_code = status_code
        self.details = details or []


def error_response(
    code: str,
    message: str,
    status_code: int,
    details: list[dict[str, str]] | None = None,
) -> JSONResponse:
    return JSONResponse(
        status_code=status_code,
        content={
            "error": {
                "code": code,
                "message": message,
                "details": details or [],
            }
        },
    )


async def app_error_handler(_request: Request, exc: AppError) -> JSONResponse:
    return error_response(exc.code, exc.message, exc.status_code, exc.details)


async def http_exception_handler(
    _request: Request, exc: StarletteHTTPException
) -> JSONResponse:
    if isinstance(exc.detail, dict) and "error" in exc.detail:
        return JSONResponse(status_code=exc.status_code, content=exc.detail)
    return error_response("HTTP_ERROR", str(exc.detail), exc.status_code)


async def validation_exception_handler(
    _request: Request, exc: RequestValidationError
) -> JSONResponse:
    details = [
        {
            "field": ".".join(str(loc) for loc in err["loc"] if loc != "body"),
            "message": err["msg"],
        }
        for err in exc.errors()
    ]
    return error_response(
        "VALIDATION_ERROR",
        "リクエストの形式が正しくありません",
        400,
        details,
    )


_jwt_verifier = JWTVerifier(
    secret_key=settings.secret_key,
    algorithm=settings.algorithm,
    cookie_name=settings.cookie_name,
)


def get_current_aid(request: Request) -> int:
    if settings.debug:
        return settings.debug_aid

    claims = _jwt_verifier.verify_request(request)
    sub = claims.get("sub")
    if sub is None:
        raise HTTPException(status_code=401, detail="認証トークンにユーザー ID がありません")
    try:
        return int(str(sub))
    except ValueError as exc:
        raise HTTPException(
            status_code=401, detail="認証トークンのユーザー ID が不正です"
        ) from exc


def get_aid_dependency():
    def _get_aid(request: Request) -> int:
        return get_current_aid(request)

    return _get_aid
