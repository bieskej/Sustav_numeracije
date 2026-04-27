from __future__ import annotations

from psycopg import Connection


def get_utilization_report(
    conn: Connection,
    *,
    region_id: int | None = None,
    opcina_id: int | None = None,
    lokacija_id: int | None = None,
    raspon_id: int | None = None,
) -> list[dict]:
    where = ["1=1"]
    params: list[object] = []
    if region_id:
        where.append("r.id = %s")
        params.append(region_id)
    if opcina_id:
        where.append("o.id = %s")
        params.append(opcina_id)
    if lokacija_id:
        where.append("l.id = %s")
        params.append(lokacija_id)
    if raspon_id:
        where.append("rm.id = %s")
        params.append(raspon_id)
    ws = " AND ".join(where)

    rows = conn.execute(
        f"""
        SELECT
            reg.naziv AS region_naziv,
            o.naziv AS opcina_naziv,
            l.naziv AS lokacija_naziv,
            rm.naziv AS raspon_naziv,
            rm.msisdn_od,
            rm.msisdn_do,
            COUNT(CASE WHEN m.status = 'slobodan' THEN 1 END) AS slobodan_count,
            COUNT(CASE WHEN m.status = 'zauzet' THEN 1 END) AS zauzet_count,
            COUNT(CASE WHEN m.status = 'karantena' THEN 1 END) AS karantena_count
        FROM region reg
        JOIN opcine o ON o.region_id = reg.id
        JOIN lokacije l ON l.opcina_id = o.id
        JOIN rasponi_msisdn rm ON rm.lokacija_id = l.id
        LEFT JOIN msisdn_brojevi m ON m.raspon_id = rm.id
        WHERE {ws}
        GROUP BY reg.naziv, o.naziv, l.naziv, rm.naziv, rm.msisdn_od, rm.msisdn_do
        ORDER BY reg.naziv, o.naziv, l.naziv, rm.msisdn_od
        """,
        params,
    ).fetchall()
    return rows