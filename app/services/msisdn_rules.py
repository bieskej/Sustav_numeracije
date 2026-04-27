from __future__ import annotations

from psycopg import Connection


def validate_msisdn_digits(msisdn: str) -> None:
    if not msisdn.isdigit():
        raise ValueError("MSISDN mora sadržavati samo znamenke")


def validate_geo_prefix(conn: Connection, msisdn: str) -> None:
    """
    Geographic-only rule: MSISDN must start with a known geographic prefix extracted
    from Plan numeracije.
    """
    prefix_count = conn.execute("SELECT COUNT(*) AS c FROM geo_prefix").fetchone()["c"]
    if prefix_count == 0:
        # Fresh installs may not have imported plan numeracije yet.
        # In that case we allow range creation instead of blocking the app entirely.
        return

    # longest prefix match
    for n in range(min(6, len(msisdn)), 1, -1):
        pref = msisdn[:n]
        row = conn.execute("SELECT 1 FROM geo_prefix WHERE prefix=%s", (pref,)).fetchone()
        if row:
            return
    raise ValueError("Nevažeći geografski prefiks (Plan numeracije)")


def validate_msisdn_in_range(msisdn: int, od: int, do: int) -> None:
    if msisdn < od or msisdn > do:
        raise ValueError("MSISDN nije unutar odabranog raspona")

