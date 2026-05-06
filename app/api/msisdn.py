from __future__ import annotations

import datetime

from fastapi import APIRouter, Depends, HTTPException, Query
from psycopg import Connection
from psycopg.errors import UniqueViolation, ForeignKeyViolation

from app.api.deps import db_dep
from app.crud import msisdn as crud
from app.models.msisdn import MsisdnCreateIn, MsisdnUpdateIn
from app.services.msisdn_rules import (
    validate_geo_prefix,
    validate_msisdn_digits,
    validate_msisdn_in_range,
)


router = APIRouter(prefix="/msisdn", tags=["msisdn"])


@router.get("")
def list_msisdn(
    raspon_id: int | None = Query(default=None, ge=1),
    status: str | None = Query(default=None, pattern="^(slobodan|zauzet|karantena)$"),
    search: str | None = None,
    page: int = Query(1, ge=1),
    per_page: int = Query(50, ge=1, le=500),
    conn: Connection = Depends(db_dep),
):
    return crud.list_msisdn(
        conn,
        raspon_id=raspon_id,
        status=status,
        search=search,
        page=page,
        per_page=per_page,
    )


@router.get("/{id}")
def get_msisdn(id: int, conn: Connection = Depends(db_dep)):
    row = crud.get_msisdn(conn, id)
    if not row:
        raise HTTPException(404, "MSISDN nije pronađen")
    return row


@router.post("", status_code=201)
def create_msisdn(data: MsisdnCreateIn, conn: Connection = Depends(db_dep)):
    validate_msisdn_digits(data.msisdn)
    try:
        validate_geo_prefix(conn, data.msisdn)
    except ValueError as e:
        raise HTTPException(400, str(e))

    raspon = conn.execute(
        "SELECT msisdn_od, msisdn_do FROM rasponi_msisdn WHERE id=%s",
        (data.raspon_id,),
    ).fetchone()
    if not raspon:
        raise HTTPException(400, "Nepostojeći raspon")

    msisdn_int = int(data.msisdn)
    try:
        validate_msisdn_in_range(msisdn_int, int(raspon["msisdn_od"]), int(raspon["msisdn_do"]))
    except ValueError as e:
        raise HTTPException(400, str(e))

    try:
        return crud.create_msisdn(conn, raspon_id=data.raspon_id, msisdn=msisdn_int)
    except UniqueViolation:
        raise HTTPException(400, "MSISDN već postoji")
    except ForeignKeyViolation:
        raise HTTPException(400, "Nepostojeći raspon")


@router.put("/{id}")
def update_msisdn(id: int, data: MsisdnUpdateIn, conn: Connection = Depends(db_dep)):
    # Get current status
    current = conn.execute("SELECT status, raspon_id, msisdn FROM msisdn_brojevi WHERE id=%s", (id,)).fetchone()
    if not current:
        raise HTTPException(404, "MSISDN nije pronađen")

    old_status = current["status"]
    raspon_id = current["raspon_id"]
    msisdn = current["msisdn"]

    # Auto-compute karantena expiry date when entering quarantine.
    # datum_karantene is the DATE ON WHICH quarantine expires (not the start date).
    datum_karantene = data.datum_karantene
    if data.status == "karantena" and not datum_karantene:
        expiry = datetime.date.today() + datetime.timedelta(days=data.karantena_trajanje_dana)
        datum_karantene = expiry.isoformat()

    row = crud.update_msisdn(
        conn,
        id=id,
        status=data.status,
        ime=data.ime,
        prezime=data.prezime,
        jmbg=data.jmbg,
        datum_dodjele=data.datum_dodjele,
        datum_karantene=datum_karantene,
        napomena=data.napomena,
    )
    if not row:
        raise HTTPException(404, "MSISDN nije pronađen")

    # Log event if status changed
    if data.status and data.status != old_status:
        from app.crud import assignment_event as crud_event
        from app.services.allocation import get_lokacija_from_raspon

        lokacija_id = get_lokacija_from_raspon(conn, raspon_id)
        action = "released" if data.status == "slobodan" else "quarantine" if data.status == "karantena" else "allocated"
        crud_event.create_assignment_event(
            conn,
            action=action,
            msisdn=msisdn,
            raspon_id=raspon_id,
            lokacija_id=lokacija_id,
            ime=data.ime,
            prezime=data.prezime,
            jmbg=data.jmbg,
            napomena=data.napomena,
        )

    return crud.get_msisdn(conn, id)


@router.delete("/{id}", status_code=204)
def delete_msisdn(id: int, conn: Connection = Depends(db_dep)):
    n = crud.delete_msisdn(conn, id)
    if n == 0:
        raise HTTPException(404, "MSISDN nije pronađen")

