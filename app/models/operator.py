from __future__ import annotations

from pydantic import BaseModel, Field


class OperatorIn(BaseModel):
    naziv: str = Field(..., min_length=1, max_length=200)


class OperatorOut(BaseModel):
    id: int
    naziv: str

