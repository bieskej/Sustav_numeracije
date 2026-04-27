from __future__ import annotations

from psycopg import Connection


def list_msisdn(
    conn: Connection,
    *,
    raspon_id: int | None,
    status: str | None,
    search: str | None,
    page: int,
    per_page: int,
) -> dict:
    where = ["1=1"]
    params: list[object] = []

    if raspon_id:
        where.append("m.raspon_id=%s")
        params.append(raspon_id)
    if status:
        where.append("m.status=%s")
        params.append(status)
    if search:
        where.append(
            "(CAST(m.msisdn AS TEXT) LIKE %s OR m.ime ILIKE %s OR m.prezime ILIKE %s OR m.oib LIKE %s)"
        )
        s = f"%{search}%"
        params.extend([s, s, s, s])

    ws = " AND ".join(where)
    total = conn.execute(
        f"SELECT COUNT(*) AS c FROM msisdn_brojevi m WHERE {ws}", params
    ).fetchone()["c"]

    offset = (page - 1) * per_page
    rows = conn.execute(
        f"""
        SELECT m.*, r.msisdn_od, r.msisdn_do, l.naziv AS lokacija_naziv, o.naziv AS opcina_naziv
        FROM msisdn_brojevi m
        JOIN rasponi_msisdn r ON r.id=m.raspon_id
        JOIN lokacije l ON l.id=r.lokacija_id
        JOIN opcine o ON o.id=l.opcina_id
        WHERE {ws}
        ORDER BY m.msisdn
        LIMIT %s OFFSET %s
        """,
        params + [per_page, offset],
    ).fetchall()

    return {
        "total": total,
        "page": page,
        "per_page": per_page,
        "pages": (total + per_page - 1) // per_page,
        "data": rows,
    }


def get_msisdn(conn: Connection, id: int) -> dict | None:
    return conn.execute(
        """
        SELECT m.*, l.naziv AS lokacija_naziv, o.naziv AS opcina_naziv
        FROM msisdn_brojevi m
        JOIN rasponi_msisdn r ON r.id=m.raspon_id
        JOIN lokacije l ON l.id=r.lokacija_id
        JOIN opcine o ON o.id=l.opcina_id
        WHERE m.id=%s
        """,
        (id,),
    ).fetchone()


def create_msisdn(conn: Connection, *, raspon_id: int, msisdn: int) -> dict:
    return conn.execute(
        """
        INSERT INTO msisdn_brojevi (raspon_id, msisdn)
        VALUES (%s, %s)
        RETURNING *
        """,
        (raspon_id, msisdn),
    ).fetchone()


def update_msisdn(
    conn: Connection,
    *,
    id: int,
    status: str,
    ime: str | None,
    prezime: str | None,
    oib: str | None,
    datum_dodjele: str | None,
    datum_karantene: str | None,
    napomena: str | None,
) -> dict | None:
    if status == "slobodan":
        return conn.execute(
            """
            UPDATE msisdn_brojevi
            SET status=%s,
                ime=NULL,
                prezime=NULL,
                oib=NULL,
                datum_dodjele=NULL,
                datum_karantene=NULL,
                napomena=%s
            WHERE id=%s
            RETURNING *
            """,
            (status, napomena, id),
        ).fetchone()

    return conn.execute(
        """
        UPDATE msisdn_brojevi
        SET status=%s,
            ime=%s,
            prezime=%s,
            oib=%s,
            datum_dodjele=%s::date,
            datum_karantene=%s::date,
            napomena=%s
        WHERE id=%s
        RETURNING *
        """,
        (status, ime, prezime, oib, datum_dodjele, datum_karantene, napomena, id),
    ).fetchone()


def delete_msisdn(conn: Connection, id: int) -> int:
    return conn.execute("DELETE FROM msisdn_brojevi WHERE id=%s", (id,)).rowcount

