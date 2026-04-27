from __future__ import annotations

from psycopg import Connection

from app.crud.pagination import page_envelope
from app.utils.normalize import normalize_name


def list_lokacije(
    conn: Connection, *, opcina_id: int | None, search: str | None, page: int, per_page: int
) -> dict:
    where = ["1=1"]
    params: list[object] = []
    if opcina_id:
        where.append("l.opcina_id=%s")
        params.append(opcina_id)
    if search:
        where.append("(l.naziv ILIKE %s OR o.naziv ILIKE %s)")
        s = f"%{search}%"
        params.extend([s, s])
    ws = " AND ".join(where)

    total = conn.execute(
        f"""
        SELECT COUNT(*)::int AS c
        FROM lokacije l
        JOIN opcine o ON o.id=l.opcina_id
        WHERE {ws}
        """,
        params,
    ).fetchone()["c"]

    offset = (page - 1) * per_page
    rows = conn.execute(
        f"""
        SELECT l.*, o.naziv AS opcina_naziv,
               COUNT(DISTINCT u.id) AS broj_uredjaja,
               COUNT(DISTINCT r.id) AS broj_raspona
        FROM lokacije l
        JOIN opcine o ON o.id = l.opcina_id
        LEFT JOIN uredjaji u ON u.lokacija_id = l.id
        LEFT JOIN rasponi_msisdn r ON r.lokacija_id = l.id
        WHERE {ws}
        GROUP BY l.id, o.naziv
        ORDER BY o.naziv, l.naziv
        LIMIT %s OFFSET %s
        """,
        params + [per_page, offset],
    ).fetchall()
    return page_envelope(total=total, page=page, per_page=per_page, data=rows)


__all__ = [
    "list_lokacije",
    "get_lokacija",
    "create_lokacija",
    "update_lokacija",
    "delete_lokacija",
]


def get_lokacija(conn: Connection, id: int) -> dict | None:
    return conn.execute(
        """
        SELECT l.*, o.naziv AS opcina_naziv
        FROM lokacije l
        JOIN opcine o ON o.id = l.opcina_id
        WHERE l.id=%s
        """,
        (id,),
    ).fetchone()


def create_lokacija(
    conn: Connection, opcina_id: int, naziv: str, adresa: str | None
) -> dict:
    naziv_norm = normalize_name(naziv)
    return conn.execute(
        """
        INSERT INTO lokacije (opcina_id, naziv, naziv_norm, adresa)
        VALUES (%s, %s, %s, %s)
        RETURNING *
        """,
        (opcina_id, naziv.strip(), naziv_norm, adresa),
    ).fetchone()


def update_lokacija(
    conn: Connection, id: int, opcina_id: int, naziv: str, adresa: str | None
) -> dict | None:
    naziv_norm = normalize_name(naziv)
    return conn.execute(
        """
        UPDATE lokacije
        SET opcina_id=%s, naziv=%s, naziv_norm=%s, adresa=%s
        WHERE id=%s
        RETURNING *
        """,
        (opcina_id, naziv.strip(), naziv_norm, adresa, id),
    ).fetchone()


def delete_lokacija(conn: Connection, id: int) -> int:
    return conn.execute("DELETE FROM lokacije WHERE id=%s", (id,)).rowcount

