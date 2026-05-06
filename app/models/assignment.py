from __future__ import annotations

from pydantic import BaseModel, Field, computed_field


class AllocationIn(BaseModel):
    postal_code: str = Field(..., min_length=3, max_length=10)
    ime: str | None = Field(default=None, max_length=200)
    prezime: str | None = Field(default=None, max_length=200)
    jmbg: str | None = Field(default=None, pattern=r'^\d{13}$')
    napomena: str | None = Field(default=None, max_length=500)


class AllocationOut(BaseModel):
    msisdn: int
    lokacija_id: int
    lokacija_naziv: str
    opcina_naziv: str
    region_naziv: str

    @computed_field  # type: ignore[misc]
    @property
    def broj(self) -> str:
        return f"+387{self.msisdn}"
