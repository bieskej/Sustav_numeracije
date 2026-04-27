from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Query
from psycopg import Connection
from psycopg.errors import UniqueViolation, ForeignKeyViolation, CheckViolation

from app.api.deps import db_dep
from app.crud import uredjaj as crud
from app.models.uredjaj import UredjajIn


router = APIRouter(prefix="/uredjaji", tags=["uredjaji"])


@router.get("")
def list_uredjaji(
    lokacija_id: int | None = Query(default=None, ge=1),
    search: str | None = None,
    page: int = Query(1, ge=1),
    per_page: int = Query(50, ge=1, le=500),
    conn: Connection = Depends(db_dep),
):
    return crud.list_uredjaji(
        conn, lokacija_id=lokacija_id, search=search, page=page, per_page=per_page
    )["data"]


@router.get("/{id}")
def get_uredjaj(id: int, conn: Connection = Depends(db_dep)):
    row = crud.get_uredjaj(conn, id)
    if not row:
        raise HTTPException(404, "Uređaj nije pronađen")
    return row


@router.post("", status_code=201)
def create_uredjaj(data: UredjajIn, conn: Connection = Depends(db_dep)):
    try:
        return crud.create_uredjaj(
            conn,
            data.lokacija_id,
            data.naziv,
            data.tip,
            data.serijski_broj,
            data.aktivan,
        )
    except ForeignKeyViolation:
        raise HTTPException(400, "Nepostojeća lokacija")
    except CheckViolation:
        raise HTTPException(400, "Neispravan tip uređaja")
    except UniqueViolation:
        raise HTTPException(400, "Uređaj već postoji na toj lokaciji")


@router.put("/{id}")
def update_uredjaj(id: int, data: UredjajIn, conn: Connection = Depends(db_dep)):
    try:
        row = crud.update_uredjaj(
            conn,
            id,
            data.lokacija_id,
            data.naziv,
            data.tip,
            data.serijski_broj,
            data.aktivan,
        )
    except ForeignKeyViolation:
        raise HTTPException(400, "Nepostojeća lokacija")
    except CheckViolation:
        raise HTTPException(400, "Neispravan tip uređaja")
    except UniqueViolation:
        raise HTTPException(400, "Uređaj već postoji na toj lokaciji")
    if not row:
        raise HTTPException(404, "Uređaj nije pronađen")
    return row


@router.delete("/{id}", status_code=204)
def delete_uredjaj(id: int, conn: Connection = Depends(db_dep)):
    n = crud.delete_uredjaj(conn, id)
    if n == 0:
        raise HTTPException(404, "Uređaj nije pronađen")

