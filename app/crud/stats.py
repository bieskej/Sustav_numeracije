from __future__ import annotations

from psycopg import Connection


def get_statistike(conn: Connection) -> dict:
    def q(sql: str) -> int:
        return conn.execute(sql).fetchone()["count"]

    zauzeti = q("SELECT COUNT(*)::int AS count FROM msisdn_brojevi WHERE status='zauzet'")
    karantena = q("SELECT COUNT(*)::int AS count FROM msisdn_brojevi WHERE status='karantena'")
    ukupno = q("SELECT COUNT(*)::int AS count FROM msisdn_brojevi")

    iskoristivost = round((zauzeti + karantena) / ukupno * 100, 1) if ukupno else 0.0

    # Approximate previous-month utilization using assignment_event history.
    # Count allocations vs releases that happened more than 30 days ago to
    # estimate how many numbers were "in use" at that point.
    trend_row = conn.execute(
        """
        SELECT
            COUNT(*) FILTER (WHERE action = 'allocated'
                             AND timestamp <= now() - INTERVAL '30 days') AS alloc_past,
            COUNT(*) FILTER (WHERE action IN ('released', 'quarantine')
                             AND timestamp <= now() - INTERVAL '30 days') AS release_past
        FROM assignment_event
        """
    ).fetchone()
    past_zauzeti = max(0, (trend_row["alloc_past"] or 0) - (trend_row["release_past"] or 0))
    past_iskoristivost = round(past_zauzeti / ukupno * 100, 1) if ukupno else 0.0
    iskoristivost_trend = round(iskoristivost - past_iskoristivost, 1)

    return {
        "opcine": q("SELECT COUNT(*)::int AS count FROM opcine"),
        "lokacije": q("SELECT COUNT(*)::int AS count FROM lokacije"),
        "uredjaji": q("SELECT COUNT(*)::int AS count FROM uredjaji"),
        "rasponi": q("SELECT COUNT(*)::int AS count FROM rasponi_msisdn"),
        "ukupno_msisdn": ukupno,
        "slobodni": q("SELECT COUNT(*)::int AS count FROM msisdn_brojevi WHERE status='slobodan'"),
        "zauzeti": zauzeti,
        "karantena": karantena,
        "iskoristivost": iskoristivost,
        "iskoristivost_trend": iskoristivost_trend,
    }
