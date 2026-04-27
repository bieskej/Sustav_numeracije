from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Query
from psycopg import Connection
from psycopg.errors import UniqueViolation, ForeignKeyViolation

from app.api.deps import db_dep
from app.crud import postal as crud
from app.models.postal import PostalCodeIn


router = APIRouter(prefix="/postal-codes", tags=["postal-codes"])


@router.get("")
def list_postal_codes(
    opcina_id: int | None = Query(default=None, ge=1),
    search: str | None = None,
    page: int = Query(1, ge=1),
    per_page: int = Query(50, ge=1, le=500),
    conn: Connection = Depends(db_dep),
):
    return crud.list_postal_codes(
        conn, opcina_id=opcina_id, search=search, page=page, per_page=per_page
    )


@router.post("", status_code=201)
def create_postal_code(data: PostalCodeIn, conn: Connection = Depends(db_dep)):
    try:
        return crud.create_postal_code(
            conn,
            opcina_id=data.opcina_id,
            postanski_broj=data.postanski_broj,
            naziv_poste=data.naziv_poste,
            default_lokacija_id=data.default_lokacija_id,
        )
    except ForeignKeyViolation:
        raise HTTPException(400, "Nepostojeća općina ili lokacija")
    except UniqueViolation:
        raise HTTPException(400, "Poštanski broj već postoji za tu općinu")


@router.delete("/{id}", status_code=204)
def delete_postal_code(id: int, conn: Connection = Depends(db_dep)):
    n = crud.delete_postal_code(conn, id)
    if n == 0:
        raise HTTPException(404, "Poštanski broj nije pronađen")

