from __future__ import annotations

from psycopg import Connection

from app.crud.pagination import page_envelope


def list_postal_codes(
    conn: Connection,
    *,
    opcina_id: int | None,
    search: str | None,
    page: int,
    per_page: int,
) -> dict:
    where = ["1=1"]
    params: list[object] = []
    if opcina_id:
        where.append("p.opcina_id=%s")
        params.append(opcina_id)
    if search:
        where.append("(p.postanski_broj LIKE %s OR p.naziv_poste ILIKE %s OR o.naziv ILIKE %s)")
        s = f"%{search}%"
        params.extend([s, s, s])
    ws = " AND ".join(where)
    total = conn.execute(
        f"""
        SELECT COUNT(*)::int AS c
        FROM postal_code p
        JOIN opcine o ON o.id=p.opcina_id
        WHERE {ws}
        """,
        params,
    ).fetchone()["c"]
    offset = (page - 1) * per_page
    rows = conn.execute(
        f"""
        SELECT p.*, o.naziv AS opcina_naziv, l.naziv AS default_lokacija_naziv
        FROM postal_code p
        JOIN opcine o ON o.id=p.opcina_id
        LEFT JOIN lokacije l ON l.id=p.default_lokacija_id
        WHERE {ws}
        ORDER BY p.postanski_broj, p.naziv_poste
        LIMIT %s OFFSET %s
        """,
        params + [per_page, offset],
    ).fetchall()
    return page_envelope(total=total, page=page, per_page=per_page, data=rows)


def create_postal_code(
    conn: Connection, *, opcina_id: int, postanski_broj: str, naziv_poste: str, default_lokacija_id: int | None = None
) -> dict:
    return conn.execute(
        """
        INSERT INTO postal_code (opcina_id, postanski_broj, naziv_poste, default_lokacija_id)
        VALUES (%s, %s, %s, %s)
        RETURNING *
        """,
        (opcina_id, postanski_broj.strip(), naziv_poste.strip(), default_lokacija_id),
    ).fetchone()


def delete_postal_code(conn: Connection, id: int) -> int:
    return conn.execute("DELETE FROM postal_code WHERE id=%s", (id,)).rowcount

