from __future__ import annotations

from app.core.database import Database


def run_karantena_cleanup(db: Database) -> int:
    """Release numbers that have been in karantena for >= 30 days.

    Clears subscriber data along with the status change so released numbers
    are ready for fresh allocation.  Returns the count of numbers released.
    """
    with db.connect() as conn:
        with conn.transaction():
            result = conn.execute(
                """
                UPDATE msisdn_brojevi
                SET status        = 'slobodan',
                    ime           = NULL,
                    prezime       = NULL,
                    jmbg          = NULL,
                    datum_dodjele = NULL,
                    datum_karantene = NULL,
                    napomena      = NULL
                WHERE status = 'karantena'
                  AND datum_karantene IS NOT NULL
                  AND datum_karantene <= CURRENT_DATE - INTERVAL '30 days'
                """
            )
            return result.rowcount
