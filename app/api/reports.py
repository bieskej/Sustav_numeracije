from __future__ import annotations

from fastapi import APIRouter, Depends, Query
from psycopg import Connection

from app.api.deps import db_dep
from app.crud import assignment_event as crud_event
from app.services.reports import get_utilization_report


router = APIRouter(prefix="/reports", tags=["reports"])


@router.get("/allocations")
def list_allocations(
    action: str | None = Query(default=None, pattern=r'^(allocated|released|quarantine)$'),
    lokacija_id: int | None = Query(default=None, ge=1),
    postal_code: str | None = Query(default=None, min_length=3, max_length=10),
    page: int = Query(1, ge=1),
    per_page: int = Query(50, ge=1, le=500),
    conn: Connection = Depends(db_dep),
):
    return crud_event.list_assignment_events(
        conn,
        action=action,
        lokacija_id=lokacija_id,
        postal_code=postal_code,
        page=page,
        per_page=per_page,
    )


@router.get("/utilization")
def get_utilization(
    region_id: int | None = Query(default=None, ge=1),
    opcina_id: int | None = Query(default=None, ge=1),
    lokacija_id: int | None = Query(default=None, ge=1),
    raspon_id: int | None = Query(default=None, ge=1),
    conn: Connection = Depends(db_dep),
):
    return get_utilization_report(
        conn,
        region_id=region_id,
        opcina_id=opcina_id,
        lokacija_id=lokacija_id,
        raspon_id=raspon_id,
    )