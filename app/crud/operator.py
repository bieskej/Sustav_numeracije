from __future__ import annotations

from psycopg import Connection

from app.crud.pagination import page_envelope


def list_operatori(conn: Connection, *, search: str | None, page: int, per_page: int) -> dict:
    where = ["1=1"]
    params: list[object] = []
    if search:
        where.append("naziv ILIKE %s")
        params.append(f"%{search}%")
    ws = " AND ".join(where)

    total = conn.execute(
        f"SELECT COUNT(*)::int AS c FROM operator WHERE {ws}", params
    ).fetchone()["c"]
    offset = (page - 1) * per_page
    rows = conn.execute(
        f"SELECT * FROM operator WHERE {ws} ORDER BY naziv LIMIT %s OFFSET %s",
        params + [per_page, offset],
    ).fetchall()
    return page_envelope(total=total, page=page, per_page=per_page, data=rows)


def get_operator(conn: Connection, id: int) -> dict | None:
    return conn.execute("SELECT * FROM operator WHERE id=%s", (id,)).fetchone()


def upsert_operator(conn: Connection, naziv: str) -> dict:
    # normalize for uniqueness using a deterministic mapping at app level
    # DB uniqueness is on raw 'naziv'; we keep input trimmed and consistent.
    naziv_clean = " ".join(naziv.strip().split())
    row = conn.execute(
        """
        INSERT INTO operator (naziv)
        VALUES (%s)
        ON CONFLICT (naziv) DO UPDATE SET naziv=EXCLUDED.naziv
        RETURNING *
        """,
        (naziv_clean,),
    ).fetchone()
    return row


def update_operator(conn: Connection, id: int, naziv: str) -> dict | None:
    naziv_clean = " ".join(naziv.strip().split())
    return conn.execute(
        "UPDATE operator SET naziv=%s WHERE id=%s RETURNING *", (naziv_clean, id)
    ).fetchone()


def delete_operator(conn: Connection, id: int) -> int:
    return conn.execute("DELETE FROM operator WHERE id=%s", (id,)).rowcount

