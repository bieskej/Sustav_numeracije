from __future__ import annotations

from pydantic import BaseModel, Field


class OpcinaIn(BaseModel):
    naziv: str = Field(..., min_length=1, max_length=200)
    region_id: int = Field(..., ge=1)


class OpcinaOut(BaseModel):
    id: int
    naziv: str
    region_id: int
    region_naziv: str | None = None
    created_at: str | None = None

