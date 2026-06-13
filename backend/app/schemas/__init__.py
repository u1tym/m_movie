from datetime import datetime
from typing import Any

from pydantic import BaseModel, Field


class ErrorDetail(BaseModel):
    field: str = ""
    message: str


class ErrorBody(BaseModel):
    code: str
    message: str
    details: list[ErrorDetail] = Field(default_factory=list)


class Pagination(BaseModel):
    page: int
    per_page: int
    total_count: int
    total_pages: int


class PaginatedResponse(BaseModel):
    items: list[Any]
    pagination: Pagination


def build_pagination(page: int, per_page: int, total_count: int) -> Pagination:
    per_page = min(max(per_page, 1), 100)
    page = max(page, 1)
    total_pages = max((total_count + per_page - 1) // per_page, 1) if total_count > 0 else 1
    return Pagination(
        page=page,
        per_page=per_page,
        total_count=total_count,
        total_pages=total_pages,
    )


def normalize_page(page: int, per_page: int) -> tuple[int, int, int]:
    per_page = min(max(per_page, 1), 100)
    page = max(page, 1)
    offset = (page - 1) * per_page
    return page, per_page, offset
