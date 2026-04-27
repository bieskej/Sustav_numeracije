from __future__ import annotations

from pydantic import BaseModel, Field, field_validator

from app.utils.normalize import digits_only


MSISDN_STATUS_RE = "^(slobodan|zauzet|karantena)$"


class MsisdnCreateIn(BaseModel):
    raspon_id: int = Field(..., ge=1)
    msisdn: str

    @field_validator("msisdn")
    @classmethod
    def _digits_only(cls, v: str) -> str:
        return digits_only(v)


class MsisdnUpdateIn(BaseModel):
    status: str = Field(..., pattern=MSISDN_STATUS_RE)
    ime: str | None = Field(default=None, max_length=100)
    prezime: str | None = Field(default=None, max_length=100)
    oib: str | None = None
    datum_dodjele: str | None = None
    datum_karantene: str | None = None
    napomena: str | None = Field(default=None, max_length=500)

    @field_validator("oib")
    @classmethod
    def _oib_check(cls, v: str | None) -> str | None:
        if v is None or v == "":
            return None
        if len(v) != 11 or not v.isdigit():
            raise ValueError("OIB mora imati točno 11 znamenki")
        return v


class MsisdnOut(BaseModel):
    id: int
    raspon_id: int
    msisdn: int
    status: str
    ime: str | None = None
    prezime: str | None = None
    oib: str | None = None
    datum_dodjele: str | None = None
    datum_karantene: str | None = None
    napomena: str | None = None
    lokacija_naziv: str | None = None
    opcina_naziv: str | None = None
    created_at: str | None = None
    updated_at: str | None = None

