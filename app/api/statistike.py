from __future__ import annotations

from fastapi import APIRouter, Depends
from psycopg import Connection

from app.api.deps import db_dep
from app.crud.stats import get_statistike


router = APIRouter(tags=["statistike"])


@router.get("/statistike")
def statistike(conn: Connection = Depends(db_dep)):
    return get_statistike(conn)

