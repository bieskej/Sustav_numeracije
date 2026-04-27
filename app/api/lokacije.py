from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Query
from psycopg import Connection
from psycopg.errors import UniqueViolation, ForeignKeyViolation

from app.api.deps import db_dep
from app.crud import lokacija as crud
from app.models.lokacija import LokacijaIn


router = APIRouter(prefix="/lokacije", tags=["lokacije"])


@router.get("")
def list_lokacije(
    opcina_id: int | None = Query(default=None, ge=1),
    search: str | None = None,
    page: int = Query(1, ge=1),
    per_page: int = Query(50, ge=1, le=500),
    conn: Connection = Depends(db_dep),
):
    return crud.list_lokacije(
        conn, opcina_id=opcina_id, search=search, page=page, per_page=per_page
    )["data"]


@router.get("/{id}")
def get_lokacija(id: int, conn: Connection = Depends(db_dep)):
    row = crud.get_lokacija(conn, id)
    if not row:
        raise HTTPException(404, "Lokacija nije pronađena")
    return row


@router.post("", status_code=201)
def create_lokacija(data: LokacijaIn, conn: Connection = Depends(db_dep)):
    try:
        return crud.create_lokacija(conn, data.opcina_id, data.naziv, data.adresa)
    except ForeignKeyViolation:
        raise HTTPException(400, "Nepostojeća općina")
    except UniqueViolation:
        raise HTTPException(400, "Lokacija već postoji u toj općini")


@router.put("/{id}")
def update_lokacija(id: int, data: LokacijaIn, conn: Connection = Depends(db_dep)):
    try:
        row = crud.update_lokacija(conn, id, data.opcina_id, data.naziv, data.adresa)
    except ForeignKeyViolation:
        raise HTTPException(400, "Nepostojeća općina")
    except UniqueViolation:
        raise HTTPException(400, "Lokacija već postoji u toj općini")
    if not row:
        raise HTTPException(404, "Lokacija nije pronađena")
    return row


@router.delete("/{id}", status_code=204)
def delete_lokacija(id: int, conn: Connection = Depends(db_dep)):
    n = crud.delete_lokacija(conn, id)
    if n == 0:
        raise HTTPException(404, "Lokacija nije pronađena")

