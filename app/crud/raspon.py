from __future__ import annotations

from psycopg import Connection

from app.crud.pagination import page_envelope

RASPON_COLUMNS = """
    r.id,
    r.lokacija_id,
    r.operator_id,
    r.naziv,
    r.msisdn_od,
    r.msisdn_do,
    r.generirano,
    r.created_at
"""


def list_rasponi(
    conn: Connection,
    *,
    lokacija_id: int | None,
    operator_id: int | None,
    page: int,
    per_page: int,
) -> dict:
    where = ["1=1"]
    params: list[object] = []
    if lokacija_id:
        where.append("r.lokacija_id=%s")
        params.append(lokacija_id)
    if operator_id:
        where.append("r.operator_id=%s")
        params.append(operator_id)
    ws = " AND ".join(where)

    total = conn.execute(
        f"SELECT COUNT(*)::int AS c FROM rasponi_msisdn r WHERE {ws}", params
    ).fetchone()["c"]

    offset = (page - 1) * per_page
    rows = conn.execute(
        f"""
        SELECT {RASPON_COLUMNS},
               l.naziv AS lokacija_naziv, o.naziv AS opcina_naziv,
               COUNT(m.id) AS ukupno,
               SUM(CASE WHEN m.status='slobodan' THEN 1 ELSE 0 END) AS slobodni,
               SUM(CASE WHEN m.status='zauzet' THEN 1 ELSE 0 END) AS zauzeti,
               SUM(CASE WHEN m.status='karantena' THEN 1 ELSE 0 END) AS karantena
        FROM rasponi_msisdn r
        JOIN lokacije l ON l.id=r.lokacija_id
        JOIN opcine o ON o.id=l.opcina_id
        LEFT JOIN msisdn_brojevi m ON m.raspon_id=r.id
        WHERE {ws}
        GROUP BY r.id, l.naziv, o.naziv
        ORDER BY r.msisdn_od
        LIMIT %s OFFSET %s
        """,
        params + [per_page, offset],
    ).fetchall()

    return page_envelope(total=total, page=page, per_page=per_page, data=rows)


def get_raspon(conn: Connection, id: int) -> dict | None:
    return conn.execute(
        """
        SELECT
            r.id,
            r.lokacija_id,
            r.operator_id,
            r.naziv,
            r.msisdn_od,
            r.msisdn_do,
            r.generirano,
            r.created_at,
            l.naziv AS lokacija_naziv,
            o.naziv AS opcina_naziv
        FROM rasponi_msisdn r
        JOIN lokacije l ON l.id=r.lokacija_id
        JOIN opcine o ON o.id=l.opcina_id
        WHERE r.id=%s
        """,
        (id,),
    ).fetchone()


def delete_raspon(conn: Connection, id: int) -> int:
    return conn.execute("DELETE FROM rasponi_msisdn WHERE id=%s", (id,)).rowcount

