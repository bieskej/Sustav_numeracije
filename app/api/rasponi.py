from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Query
from psycopg import Connection
from psycopg.errors import ForeignKeyViolation, CheckViolation

from app.api.deps import db_dep
from app.crud import raspon as crud
from app.models.raspon import RasponIn
from app.services.raspon_service import RangeOverlapError, create_range, generate_msisdn, update_range
from app.services.msisdn_rules import validate_geo_prefix


router = APIRouter(prefix="/rasponi", tags=["rasponi"])


@router.get("")
def list_rasponi(
    lokacija_id: int | None = Query(default=None, ge=1),
    operator_id: int | None = Query(default=None, ge=1),
    page: int = Query(1, ge=1),
    per_page: int = Query(50, ge=1, le=500),
    conn: Connection = Depends(db_dep),
):
    return crud.list_rasponi(
        conn, lokacija_id=lokacija_id, operator_id=operator_id, page=page, per_page=per_page
    )["data"]


@router.get("/{id}")
def get_raspon(id: int, conn: Connection = Depends(db_dep)):
    row = crud.get_raspon(conn, id)
    if not row:
        raise HTTPException(404, "Raspon nije pronađen")
    return row


@router.post("", status_code=201)
def create_raspon(data: RasponIn, conn: Connection = Depends(db_dep)):
    od = int(data.msisdn_od)
    do = int(data.msisdn_do)
    if od >= do:
        raise HTTPException(400, "msisdn_od mora biti manji od msisdn_do")

    # geographic-only: validate prefixes exist (by checking boundary numbers)
    try:
        validate_geo_prefix(conn, str(od))
        validate_geo_prefix(conn, str(do))
    except ValueError as e:
        raise HTTPException(400, str(e))

    try:
        return create_range(
            conn,
            lokacija_id=data.lokacija_id,
            operator_id=data.operator_id,
            naziv=data.naziv,
            msisdn_od=od,
            msisdn_do=do,
        )
    except ForeignKeyViolation:
        raise HTTPException(400, "Nepostojeća lokacija ili operator")
    except CheckViolation:
        raise HTTPException(400, "Neispravan raspon")
    except RangeOverlapError as e:
        raise HTTPException(400, str(e))


@router.put("/{id}")
def update_raspon(id: int, data: RasponIn, conn: Connection = Depends(db_dep)):
    od = int(data.msisdn_od)
    do = int(data.msisdn_do)
    if od >= do:
        raise HTTPException(400, "msisdn_od mora biti manji od msisdn_do")

    try:
        validate_geo_prefix(conn, str(od))
        validate_geo_prefix(conn, str(do))
    except ValueError as e:
        raise HTTPException(400, str(e))

    try:
        row = update_range(
            conn,
            id=id,
            lokacija_id=data.lokacija_id,
            operator_id=data.operator_id,
            naziv=data.naziv,
            msisdn_od=od,
            msisdn_do=do,
        )
    except ForeignKeyViolation:
        raise HTTPException(400, "Nepostojeća lokacija ili operator")
    except CheckViolation:
        raise HTTPException(400, "Neispravan raspon")
    except RangeOverlapError as e:
        raise HTTPException(400, str(e))

    if not row:
        raise HTTPException(404, "Raspon nije pronađen")
    return row


@router.delete("/{id}", status_code=204)
def delete_raspon(id: int, conn: Connection = Depends(db_dep)):
    n = crud.delete_raspon(conn, id)
    if n == 0:
        raise HTTPException(404, "Raspon nije pronađen")


@router.post("/{id}/generiraj", status_code=201)
def generiraj_brojeve(id: int, conn: Connection = Depends(db_dep)):
    try:
        count = generate_msisdn(conn, raspon_id=id)
    except ValueError as e:
        msg = str(e)
        if msg == "Raspon nije pronađen":
            raise HTTPException(404, msg)
        raise HTTPException(400, msg)
    return {"poruka": f"Generirano {count} MSISDN brojeva", "count": count}

