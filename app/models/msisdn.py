from __future__ import annotations

from pydantic import BaseModel, Field, computed_field, field_validator, model_validator

from app.utils.normalize import digits_only, strip_international_prefix


MSISDN_STATUS_RE = "^(slobodan|zauzet|karantena)$"


def _validate_jmbg(v: str | None) -> str | None:
    if v is None or v == "":
        return None
    if len(v) != 13 or not v.isdigit():
        raise ValueError("JMBG mora imati točno 13 cifara")
    weights = [7, 6, 5, 4, 3, 2, 7, 6, 5, 4, 3, 2]
    total = sum(int(v[i]) * weights[i] for i in range(12))
    k = 11 - (total % 11)
    if k == 10:
        raise ValueError("Neispravan JMBG (kontrolna cifra nevažeća)")
    if k == 11:
        k = 0
    if k != int(v[12]):
        raise ValueError("Neispravan JMBG (kontrolna cifra ne odgovara)")
    return v


class MsisdnCreateIn(BaseModel):
    raspon_id: int = Field(..., ge=1)
    msisdn: str

    @field_validator("msisdn")
    @classmethod
    def _digits_only(cls, v: str) -> str:
        return digits_only(strip_international_prefix(v))


class MsisdnUpdateIn(BaseModel):
    status: str = Field(..., pattern=MSISDN_STATUS_RE)
    ime: str | None = Field(default=None, max_length=100)
    prezime: str | None = Field(default=None, max_length=100)
    jmbg: str | None = None
    datum_dodjele: str | None = None
    datum_karantene: str | None = None
    napomena: str | None = Field(default=None, max_length=500)

    @field_validator("jmbg")
    @classmethod
    def _jmbg_check(cls, v: str | None) -> str | None:
        return _validate_jmbg(v)


class MsisdnOut(BaseModel):
    id: int
    raspon_id: int
    msisdn: int
    status: str
    ime: str | None = None
    prezime: str | None = None
    jmbg: str | None = None
    datum_dodjele: str | None = None
    datum_karantene: str | None = None
    napomena: str | None = None
    lokacija_naziv: str | None = None
    opcina_naziv: str | None = None
    created_at: str | None = None
    updated_at: str | None = None

    @computed_field  # type: ignore[misc]
    @property
    def broj(self) -> str:
        return f"+387{self.msisdn}"
