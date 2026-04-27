from __future__ import annotations

from pydantic import BaseModel, Field, field_validator

from app.utils.normalize import digits_only


class RasponIn(BaseModel):
    lokacija_id: int = Field(..., ge=1)
    operator_id: int | None = Field(default=None, ge=1)
    naziv: str | None = Field(default=None, max_length=200)
    msisdn_od: str
    msisdn_do: str

    @field_validator("msisdn_od", "msisdn_do")
    @classmethod
    def _digits_only(cls, v: str) -> str:
        return digits_only(v)


class RasponOut(BaseModel):
    id: int
    lokacija_id: int
    operator_id: int | None = None
    naziv: str | None = None
    msisdn_od: int
    msisdn_do: int
    generirano: bool
    lokacija_naziv: str | None = None
    opcina_naziv: str | None = None
    ukupno: int | None = None
    slobodni: int | None = None
    zauzeti: int | None = None
    karantena: int | None = None

