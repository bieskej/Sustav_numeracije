from __future__ import annotations

from pydantic import BaseModel, Field


class AssignmentEventIn(BaseModel):
    action: str = Field(..., pattern=r'^(allocated|released|quarantine)$')
    msisdn: int = Field(..., ge=100000000, le=999999999)  # 9-digit MSISDN
    raspon_id: int = Field(..., ge=1)
    lokacija_id: int = Field(..., ge=1)
    postal_code: str | None = Field(default=None, min_length=3, max_length=10)
    ime: str | None = Field(default=None, max_length=200)
    prezime: str | None = Field(default=None, max_length=200)
    oib: str | None = Field(default=None, pattern=r'^\d{11}$')
    napomena: str | None = Field(default=None, max_length=500)


class AssignmentEventOut(BaseModel):
    id: int
    action: str
    msisdn: int
    raspon_id: int
    lokacija_id: int
    postal_code: str | None = None
    ime: str | None = None
    prezime: str | None = None
    oib: str | None = None
    napomena: str | None = None
    timestamp: str