from __future__ import annotations

from pydantic import BaseModel, Field


class PostalCodeIn(BaseModel):
    opcina_id: int = Field(..., ge=1)
    postanski_broj: str = Field(..., min_length=3, max_length=10)
    naziv_poste: str = Field(..., min_length=1, max_length=200)
    default_lokacija_id: int | None = Field(default=None, ge=1)


class PostalCodeOut(BaseModel):
    id: int
    opcina_id: int
    postanski_broj: str
    naziv_poste: str
    default_lokacija_id: int | None = None
    opcina_naziv: str | None = None
    default_lokacija_naziv: str | None = None

