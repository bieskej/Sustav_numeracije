from __future__ import annotations

from psycopg import Connection


def get_statistike(conn: Connection) -> dict:
    def q(sql: str) -> int:
        return conn.execute(sql).fetchone()["count"]

    return {
        "opcine": q("SELECT COUNT(*)::int AS count FROM opcine"),
        "lokacije": q("SELECT COUNT(*)::int AS count FROM lokacije"),
        "uredjaji": q("SELECT COUNT(*)::int AS count FROM uredjaji"),
        "rasponi": q("SELECT COUNT(*)::int AS count FROM rasponi_msisdn"),
        "ukupno_msisdn": q("SELECT COUNT(*)::int AS count FROM msisdn_brojevi"),
        "slobodni": q(
            "SELECT COUNT(*)::int AS count FROM msisdn_brojevi WHERE status='slobodan'"
        ),
        "zauzeti": q(
            "SELECT COUNT(*)::int AS count FROM msisdn_brojevi WHERE status='zauzet'"
        ),
        "karantena": q(
            "SELECT COUNT(*)::int AS count FROM msisdn_brojevi WHERE status='karantena'"
        ),
    }

