from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Query
from psycopg import Connection
from psycopg.errors import UniqueViolation, ForeignKeyViolation

from app.api.deps import db_dep
from app.crud import opcina as crud
from app.models.opcina import OpcinaIn


router = APIRouter(prefix="/opcine", tags=["opcine"])


@router.get("")
def list_opcine(
    search: str | None = None,
    page: int = Query(1, ge=1),
    per_page: int = Query(50, ge=1, le=500),
    conn: Connection = Depends(db_dep),
):
    return crud.list_opcine(conn, search=search, page=page, per_page=per_page)["data"]


@router.get("/{id}")
def get_opcina(id: int, conn: Connection = Depends(db_dep)):
    row = crud.get_opcina(conn, id)
    if not row:
        raise HTTPException(404, "Općina nije pronađena")
    return row


@router.post("", status_code=201)
def create_opcina(data: OpcinaIn, conn: Connection = Depends(db_dep)):
    try:
        return crud.create_opcina(conn, data.naziv, data.region_id)
    except UniqueViolation:
        raise HTTPException(400, "Naziv već postoji")


@router.put("/{id}")
def update_opcina(id: int, data: OpcinaIn, conn: Connection = Depends(db_dep)):
    try:
        row = crud.update_opcina(conn, id, data.naziv, data.region_id)
    except UniqueViolation:
        raise HTTPException(400, "Naziv već postoji")
    if not row:
        raise HTTPException(404, "Općina nije pronađena")
    return row


@router.delete("/{id}", status_code=204)
def delete_opcina(id: int, conn: Connection = Depends(db_dep)):
    try:
        n = crud.delete_opcina(conn, id)
    except ForeignKeyViolation:
        raise HTTPException(400, "Općina se koristi")
    if n == 0:
        raise HTTPException(404, "Općina nije pronađena")

