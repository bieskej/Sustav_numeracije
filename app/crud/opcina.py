from __future__ import annotations

from psycopg import Connection

from app.crud.pagination import page_envelope
from app.utils.normalize import normalize_name


def list_opcine(conn: Connection, *, search: str | None, page: int, per_page: int) -> dict:
    where = ["1=1"]
    params: list[object] = []
    if search:
        where.append("(o.naziv ILIKE %s)")
        params.append(f"%{search}%")
    ws = " AND ".join(where)

    total = conn.execute(
        f"SELECT COUNT(*)::int AS c FROM opcine o WHERE {ws}", params
    ).fetchone()["c"]
    offset = (page - 1) * per_page
    rows = conn.execute(
        f"""
        SELECT o.*, r.naziv AS region_naziv, COUNT(l.id) AS broj_lokacija
        FROM opcine o
        LEFT JOIN region r ON r.id = o.region_id
        LEFT JOIN lokacije l ON l.opcina_id = o.id
        WHERE {ws}
        GROUP BY o.id, r.naziv
        ORDER BY o.naziv
        LIMIT %s OFFSET %s
        """,
        params + [per_page, offset],
    ).fetchall()
    return page_envelope(total=total, page=page, per_page=per_page, data=rows)


def get_opcina(conn: Connection, id: int) -> dict | None:
    return conn.execute("SELECT * FROM opcine WHERE id=%s", (id,)).fetchone()


def create_opcina(conn: Connection, naziv: str, region_id: int) -> dict:
    naziv_norm = normalize_name(naziv)
    row = conn.execute(
        """
        INSERT INTO opcine (naziv, naziv_norm, region_id)
        VALUES (%s, %s, %s)
        RETURNING *
        """,
        (naziv.strip(), naziv_norm, region_id),
    ).fetchone()
    return row


def update_opcina(conn: Connection, id: int, naziv: str, region_id: int) -> dict | None:
    naziv_norm = normalize_name(naziv)
    return conn.execute(
        """
        UPDATE opcine
        SET naziv=%s, naziv_norm=%s, region_id=%s
        WHERE id=%s
        RETURNING *
        """,
        (naziv.strip(), naziv_norm, region_id, id),
    ).fetchone()


def delete_opcina(conn: Connection, id: int) -> int:
    return conn.execute("DELETE FROM opcine WHERE id=%s", (id,)).rowcount

