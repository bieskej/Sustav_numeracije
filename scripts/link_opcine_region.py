from __future__ import annotations

import os
from dotenv import load_dotenv

from app.core.database import Database, init_db
from app.utils.normalize import normalize_name


def main() -> None:
    load_dotenv()
    db_url = os.getenv("DATABASE_URL", "").strip()
    if not db_url:
        raise SystemExit("DATABASE_URL is required")

    db = Database(db_url)
    init_db(db)

    with db.connect() as conn:
        with conn.transaction():
            # 1. Kreiraj/pronađi region za Republiku Srpsku
            region = conn.execute(
                """
                INSERT INTO region (naziv, entitet)
                VALUES ('Republika Srpska', 'Republika Srpska')
                ON CONFLICT (naziv) DO NOTHING
                RETURNING id
                """,
            ).fetchone()
            
            if region:
                region_id = region["id"]
            else:
                region = conn.execute(
                    "SELECT id FROM region WHERE naziv='Republika Srpska'",
                ).fetchone()
                region_id = region["id"]
            
            # 2. Ažuriraj opcine sa region_id
            opcina_names = ["Banja Luka"]  # Za sada samo Banja Luka
            
            for opcina_naziv in opcina_names:
                opcina_norm = normalize_name(opcina_naziv)
                result = conn.execute(
                    """
                    UPDATE opcine
                    SET region_id=%s
                    WHERE naziv_norm=%s
                    RETURNING id
                    """,
                    (region_id, opcina_norm),
                )
                
                if result.rowcount > 0:
                    print(f"Ažurirana opcina: {opcina_naziv}")
                else:
                    print(f"Opcina nije pronađena: {opcina_naziv}")


if __name__ == "__main__":
    main()
