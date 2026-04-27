from __future__ import annotations

import os
from pathlib import Path

from dotenv import load_dotenv

from app.core.database import Database, init_db
from app.utils.excel_blocks_parser import parse_assigned_blocks_xlsx


def main() -> None:
    load_dotenv()
    db_url = os.getenv("DATABASE_URL", "").strip()
    if not db_url:
        raise SystemExit("DATABASE_URL is required")

    candidates = [
        Path("inputs") / "Dodijeljeni blokovi brojeva_h 18-2-2026.xlsx",
        Path("inputs") / "Dodijeljeni_blokovi_brojeva_h.xlsx",
        Path("inputs") / "Dodijeljeni blokovi brojeva.xlsx",
        Path("Dodijeljeni blokovi brojeva_h 18-2-2026.xlsx"),
        Path("Dodijeljeni_blokovi_brojeva_h.xlsx"),
    ]
    xlsx_path = next((p for p in candidates if p.exists()), None)
    if not xlsx_path:
        raise SystemExit(
            "Missing input file. Expected one of: " + ", ".join(str(p) for p in candidates)
        )

    db = Database(db_url)
    init_db(db)

    blocks = parse_assigned_blocks_xlsx(xlsx_path)
    geo_blocks = [b for b in blocks if b.tip == "geografski"]

    with db.connect() as conn:
        with conn.transaction():
            for b in geo_blocks:
                op = conn.execute(
                    """
                    INSERT INTO operator (naziv)
                    VALUES (%s)
                    ON CONFLICT (naziv) DO UPDATE SET naziv=EXCLUDED.naziv
                    RETURNING id
                    """,
                    (b.operator_name,),
                ).fetchone()

                conn.execute(
                    """
                    INSERT INTO dodijeljeni_blok (operator_id, msisdn_od, msisdn_do, tip)
                    VALUES (%s, %s, %s, %s)
                    ON CONFLICT (operator_id, msisdn_od, msisdn_do, tip) DO NOTHING
                    """,
                    (op["id"], b.msisdn_od, b.msisdn_do, b.tip),
                )

    print(
        f"Imported {len(geo_blocks)} geographic blocks (of {len(blocks)} total rows) from {xlsx_path}"
    )


if __name__ == "__main__":
    main()

