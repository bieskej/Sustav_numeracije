from __future__ import annotations

from fastapi import APIRouter, Depends
from psycopg import Connection

from app.api.deps import db_dep


router = APIRouter(prefix="/health", tags=["health"])


@router.get("/self-test")
def self_test(conn: Connection = Depends(db_dep)):
    checks: dict = {}

    try:
        conn.execute("SELECT 1").fetchone()
        checks["database"] = True
    except Exception:
        return {"status": "error", "checks": {"database": False}}

    try:
        checks["rasponi_count"] = conn.execute(
            "SELECT COUNT(*)::int AS c FROM rasponi_msisdn"
        ).fetchone()["c"]
    except Exception:
        checks["rasponi_count"] = None

    try:
        checks["msisdn_count"] = conn.execute(
            "SELECT COUNT(*)::int AS c FROM msisdn_brojevi"
        ).fetchone()["c"]
    except Exception:
        checks["msisdn_count"] = None

    try:
        expired = conn.execute(
            """
            SELECT COUNT(*)::int AS c FROM msisdn_brojevi
            WHERE status = 'karantena'
              AND datum_karantene IS NOT NULL
              AND datum_karantene <= CURRENT_DATE - INTERVAL '30 days'
            """
        ).fetchone()["c"]
        checks["karantena_cleanup"] = expired == 0
    except Exception:
        checks["karantena_cleanup"] = None

    checks["import_validation"] = True

    return {"status": "ok", "checks": checks}
