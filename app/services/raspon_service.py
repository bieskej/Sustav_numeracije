from __future__ import annotations

from psycopg import Connection
from psycopg.errors import ExclusionViolation

RETURNING_COLUMNS = """
    id,
    lokacija_id,
    operator_id,
    naziv,
    msisdn_od,
    msisdn_do,
    generirano,
    created_at
"""


class RangeOverlapError(ValueError):
    pass


def create_range(
    conn: Connection,
    *,
    lokacija_id: int,
    operator_id: int | None,
    naziv: str | None,
    msisdn_od: int,
    msisdn_do: int,
) -> dict:
    try:
        return conn.execute(
            """
            INSERT INTO rasponi_msisdn (lokacija_id, operator_id, naziv, msisdn_od, msisdn_do)
            VALUES (%s, %s, %s, %s, %s)
            RETURNING
            """
            + RETURNING_COLUMNS,
            (lokacija_id, operator_id, naziv, msisdn_od, msisdn_do),
        ).fetchone()
    except ExclusionViolation as e:
        raise RangeOverlapError("Raspon se preklapa s postojećim rasponom") from e


def update_range(
    conn: Connection,
    *,
    id: int,
    lokacija_id: int,
    operator_id: int | None,
    naziv: str | None,
    msisdn_od: int,
    msisdn_do: int,
) -> dict | None:
    try:
        return conn.execute(
            """
            UPDATE rasponi_msisdn
            SET lokacija_id=%s, operator_id=%s, naziv=%s, msisdn_od=%s, msisdn_do=%s
            WHERE id=%s
            RETURNING
            """
            + RETURNING_COLUMNS,
            (lokacija_id, operator_id, naziv, msisdn_od, msisdn_do, id),
        ).fetchone()
    except ExclusionViolation as e:
        raise RangeOverlapError("Raspon se preklapa s postojećim rasponom") from e


def generate_msisdn(conn: Connection, *, raspon_id: int, limit: int = 100_000) -> int:
    raspon = conn.execute(
        "SELECT id, msisdn_od, msisdn_do, generirano FROM rasponi_msisdn WHERE id=%s",
        (raspon_id,),
    ).fetchone()
    if not raspon:
        raise ValueError("Raspon nije pronađen")
    if raspon["generirano"]:
        raise ValueError("Već generirano")

    od = int(raspon["msisdn_od"])
    do = int(raspon["msisdn_do"])
    count = do - od + 1
    if count > limit:
        raise ValueError(f"Max {limit:,} brojeva po generiranju".replace(",", "."))

    conn.execute(
        """
        INSERT INTO msisdn_brojevi (raspon_id, msisdn)
        SELECT %s, gs
        FROM generate_series(%s, %s) AS gs
        ON CONFLICT (msisdn) DO NOTHING
        """,
        (raspon_id, od, do),
    )
    conn.execute("UPDATE rasponi_msisdn SET generirano=TRUE WHERE id=%s", (raspon_id,))
    return count

