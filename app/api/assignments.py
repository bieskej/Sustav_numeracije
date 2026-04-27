from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Query
from psycopg import Connection
from psycopg.errors import ForeignKeyViolation, UniqueViolation

from app.api.deps import db_dep
from app.models.assignment import AllocationIn, AllocationOut
from app.services.allocation import allocate_number


router = APIRouter(prefix="/assignments", tags=["assignments"])


@router.post("/allocate", status_code=201)
def allocate(data: AllocationIn, conn: Connection = Depends(db_dep)) -> AllocationOut:
    try:
        return allocate_number(conn, data)
    except ValueError as e:
        raise HTTPException(400, str(e))