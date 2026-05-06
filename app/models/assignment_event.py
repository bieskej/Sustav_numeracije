from __future__ import annotations

from pydantic import BaseModel, Field


class AssignmentEventIn(BaseModel):
    action: str = Field(..., pattern=r'^(allocated|released|quarantine)$')
    msisdn: int = Field(..., ge=10000000, le=9999999999)
    raspon_id: int = Field(..., ge=1)
    lokacija_id: int = Field(..., ge=1)
    postal_code: str | None = Field(default=None, min_length=3, max_length=10)
    ime: str | None = Field(default=None, max_length=200)
    prezime: str | None = Field(default=None, max_length=200)
    jmbg: str | None = Field(default=None, pattern=r'^\d{13}$')
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
    jmbg: str | None = None
    napomena: str | None = None
    timestamp: str
