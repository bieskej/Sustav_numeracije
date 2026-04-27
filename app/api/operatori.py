from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Query
from psycopg import Connection
from psycopg.errors import UniqueViolation, ForeignKeyViolation

from app.api.deps import db_dep
from app.crud import operator as crud
from app.models.operator import OperatorIn


router = APIRouter(prefix="/operatori", tags=["operatori"])


@router.get("")
def list_operatori(
    search: str | None = None,
    page: int = Query(1, ge=1),
    per_page: int = Query(50, ge=1, le=500),
    conn: Connection = Depends(db_dep),
):
    return crud.list_operatori(conn, search=search, page=page, per_page=per_page)


@router.get("/{id}")
def get_operator(id: int, conn: Connection = Depends(db_dep)):
    row = crud.get_operator(conn, id)
    if not row:
        raise HTTPException(404, "Operator nije pronađen")
    return row


@router.post("", status_code=201)
def create_operator(data: OperatorIn, conn: Connection = Depends(db_dep)):
    try:
        return crud.upsert_operator(conn, data.naziv)
    except UniqueViolation:
        raise HTTPException(400, "Naziv već postoji")


@router.put("/{id}")
def update_operator(id: int, data: OperatorIn, conn: Connection = Depends(db_dep)):
    try:
        row = crud.update_operator(conn, id, data.naziv)
    except UniqueViolation:
        raise HTTPException(400, "Naziv već postoji")
    if not row:
        raise HTTPException(404, "Operator nije pronađen")
    return row


@router.delete("/{id}", status_code=204)
def delete_operator(id: int, conn: Connection = Depends(db_dep)):
    try:
        n = crud.delete_operator(conn, id)
    except ForeignKeyViolation:
        raise HTTPException(400, "Operator se koristi")
    if n == 0:
        raise HTTPException(404, "Operator nije pronađen")

