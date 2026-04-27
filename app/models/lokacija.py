from __future__ import annotations

from pydantic import BaseModel, Field


class LokacijaIn(BaseModel):
    opcina_id: int = Field(..., ge=1)
    naziv: str = Field(..., min_length=1, max_length=200)
    adresa: str | None = Field(default=None, max_length=300)


class LokacijaOut(BaseModel):
    id: int
    opcina_id: int
    naziv: str
    adresa: str | None = None
    opcina_naziv: str | None = None
    created_at: str | None = None

