from __future__ import annotations

from psycopg import Connection

from app.crud.pagination import page_envelope
from app.utils.normalize import normalize_name


def list_uredjaji(
    conn: Connection, *, lokacija_id: int | None, search: str | None, page: int, per_page: int
) -> dict:
    where = ["1=1"]
    params: list[object] = []
    if lokacija_id:
        where.append("u.lokacija_id=%s")
        params.append(lokacija_id)
    if search:
        where.append("(u.naziv ILIKE %s OR l.naziv ILIKE %s OR o.naziv ILIKE %s)")
        s = f"%{search}%"
        params.extend([s, s, s])
    ws = " AND ".join(where)

    total = conn.execute(
        f"""
        SELECT COUNT(*)::int AS c
        FROM uredjaji u
        JOIN lokacije l ON l.id=u.lokacija_id
        JOIN opcine o ON o.id=l.opcina_id
        WHERE {ws}
        """,
        params,
    ).fetchone()["c"]
    offset = (page - 1) * per_page
    rows = conn.execute(
        f"""
        SELECT u.*, l.naziv AS lokacija_naziv, o.naziv AS opcina_naziv
        FROM uredjaji u
        JOIN lokacije l ON l.id = u.lokacija_id
        JOIN opcine o ON o.id = l.opcina_id
        WHERE {ws}
        ORDER BY o.naziv, l.naziv, u.naziv
        LIMIT %s OFFSET %s
        """,
        params + [per_page, offset],
    ).fetchall()
    return page_envelope(total=total, page=page, per_page=per_page, data=rows)


def get_uredjaj(conn: Connection, id: int) -> dict | None:
    return conn.execute(
        """
        SELECT u.*, l.naziv AS lokacija_naziv, o.naziv AS opcina_naziv
        FROM uredjaji u
        JOIN lokacije l ON l.id = u.lokacija_id
        JOIN opcine o ON o.id = l.opcina_id
        WHERE u.id=%s
        """,
        (id,),
    ).fetchone()


def create_uredjaj(
    conn: Connection,
    lokacija_id: int,
    naziv: str,
    tip: str,
    serijski_broj: str | None,
    aktivan: bool,
) -> dict:
    naziv_norm = normalize_name(naziv)
    return conn.execute(
        """
        INSERT INTO uredjaji (lokacija_id, naziv, naziv_norm, tip, serijski_broj, aktivan)
        VALUES (%s, %s, %s, %s, %s, %s)
        RETURNING *
        """,
        (lokacija_id, naziv.strip(), naziv_norm, tip, serijski_broj, aktivan),
    ).fetchone()


def update_uredjaj(
    conn: Connection,
    id: int,
    lokacija_id: int,
    naziv: str,
    tip: str,
    serijski_broj: str | None,
    aktivan: bool,
) -> dict | None:
    naziv_norm = normalize_name(naziv)
    return conn.execute(
        """
        UPDATE uredjaji
        SET lokacija_id=%s, naziv=%s, naziv_norm=%s, tip=%s, serijski_broj=%s, aktivan=%s
        WHERE id=%s
        RETURNING *
        """,
        (lokacija_id, naziv.strip(), naziv_norm, tip, serijski_broj, aktivan, id),
    ).fetchone()


def delete_uredjaj(conn: Connection, id: int) -> int:
    return conn.execute("DELETE FROM uredjaji WHERE id=%s", (id,)).rowcount

