from __future__ import annotations

from app.core.database import Database


def run_karantena_cleanup(db: Database) -> int:
    """Release numbers whose karantena expiry date (datum_karantene) has passed.

    datum_karantene holds the DATE ON WHICH quarantine expires, so we simply
    release all rows where that date is today or earlier.  Clears subscriber
    data so the number is ready for fresh allocation.
    Returns the count of numbers released.
    """
    with db.connect() as conn:
        with conn.transaction():
            result = conn.execute(
                """
                UPDATE msisdn_brojevi
                SET status          = 'slobodan',
                    ime             = NULL,
                    prezime         = NULL,
                    jmbg            = NULL,
                    datum_dodjele   = NULL,
                    datum_karantene = NULL,
                    napomena        = NULL
                WHERE status = 'karantena'
                  AND datum_karantene IS NOT NULL
                  AND datum_karantene <= CURRENT_DATE
                """
            )
            return result.rowcount
