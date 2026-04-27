from __future__ import annotations

from pydantic import BaseModel, Field


class RegionIn(BaseModel):
    naziv: str = Field(..., min_length=1, max_length=200)
    entitet: str = Field(default="Republika Srpska", min_length=1, max_length=100)


class RegionOut(BaseModel):
    id: int
    naziv: str
    entitet: str


class GeoPrefixIn(BaseModel):
    prefix: str = Field(..., min_length=2, max_length=6)
    region_id: int = Field(..., ge=1)
    source: str | None = Field(default=None, max_length=200)


class GeoPrefixOut(BaseModel):
    prefix: str
    region_id: int
    source: str | None = None

