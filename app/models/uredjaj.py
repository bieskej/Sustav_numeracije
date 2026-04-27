from __future__ import annotations

from pydantic import BaseModel, Field


class UredjajIn(BaseModel):
    lokacija_id: int = Field(..., ge=1)
    naziv: str = Field(..., min_length=1, max_length=200)
    tip: str = Field(..., pattern="^(MSAN|GPON_OLT)$")
    serijski_broj: str | None = Field(default=None, max_length=100)
    aktivan: bool = True


class UredjajOut(BaseModel):
    id: int
    lokacija_id: int
    naziv: str
    tip: str
    serijski_broj: str | None = None
    aktivan: bool
    lokacija_naziv: str | None = None
    opcina_naziv: str | None = None
    created_at: str | None = None

