from __future__ import annotations

from pydantic import BaseModel, Field


class Page(BaseModel):
    total: int
    page: int
    per_page: int
    pages: int


class PageResult(Page):
    data: list[dict]


class IdResponse(BaseModel):
    id: int = Field(..., ge=1)

