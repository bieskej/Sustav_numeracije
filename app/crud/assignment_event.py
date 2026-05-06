from __future__ import annotations

from psycopg import Connection

from app.crud.pagination import page_envelope


def list_assignment_events(
    conn: Connection,
    *,
    action: str | None = None,
    lokacija_id: int | None = None,
    postal_code: str | None = None,
    page: int,
    per_page: int,
) -> dict:
    where = ["1=1"]
    params: list[object] = []
    if action:
        where.append("ae.action = %s")
        params.append(action)
    if lokacija_id:
        where.append("ae.lokacija_id = %s")
        params.append(lokacija_id)
    if postal_code:
        where.append("ae.postal_code = %s")
        params.append(postal_code)
    ws = " AND ".join(where)

    total = conn.execute(
        f"SELECT COUNT(*)::int AS c FROM assignment_event ae WHERE {ws}", params
    ).fetchone()["c"]
    offset = (page - 1) * per_page
    rows = conn.execute(
        f"""
        SELECT ae.*, l.naziv AS lokacija_naziv, r.naziv AS raspon_naziv
        FROM assignment_event ae
        LEFT JOIN lokacije l ON l.id = ae.lokacija_id
        LEFT JOIN rasponi_msisdn r ON r.id = ae.raspon_id
        WHERE {ws}
        ORDER BY ae.timestamp DESC
        LIMIT %s OFFSET %s
        """,
        params + [per_page, offset],
    ).fetchall()
    return page_envelope(total=total, page=page, per_page=per_page, data=rows)


def create_assignment_event(
    conn: Connection,
    *,
    action: str,
    msisdn: int,
    raspon_id: int,
    lokacija_id: int,
    postal_code: str | None = None,
    ime: str | None = None,
    prezime: str | None = None,
    jmbg: str | None = None,
    napomena: str | None = None,
) -> dict:
    return conn.execute(
        """
        INSERT INTO assignment_event (action, msisdn, raspon_id, lokacija_id, postal_code, ime, prezime, jmbg, napomena)
        VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
        RETURNING *
        """,
        (action, msisdn, raspon_id, lokacija_id, postal_code, ime, prezime, jmbg, napomena),
    ).fetchone()
