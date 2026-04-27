from __future__ import annotations

import os
from pathlib import Path

from dotenv import load_dotenv

from app.core.database import Database, init_db
from app.utils.plan_numeracije_parser import extract_prefix_records


def main() -> None:
    load_dotenv()
    db_url = os.getenv("DATABASE_URL", "").strip()
    if not db_url:
        raise SystemExit("DATABASE_URL is required")

    # You indicated `Spisak-posta.pdf` is your plan numeracije source.
    # We search a few common locations/names for convenience.
    candidates = [
        Path("inputs") / "Plan numeracije.pdf",
        Path("inputs") / "Spisak-posta.pdf",
        Path("inputs") / "spisak-posta.pdf",
        Path("Spisak-posta.pdf"),
        Path("spisak-posta.pdf"),
    ]
    pdf_path = next((p for p in candidates if p.exists()), None)
    if not pdf_path:
        raise SystemExit(
            "Missing plan numeracije PDF. Expected one of: "
            + ", ".join(str(p) for p in candidates)
        )

    db = Database(db_url)
    init_db(db)

    records = extract_prefix_records(pdf_path)
    if not records:
        raise SystemExit(
            "No prefixes extracted. Update parser regex in app/utils/plan_numeracije_parser.py."
        )

    with db.connect() as conn:
        with conn.transaction():
            for rec in records:
                region = conn.execute(
                    """
                    INSERT INTO region (naziv, entitet)
                    VALUES (%s, 'Republika Srpska')
                    ON CONFLICT (naziv) DO UPDATE SET naziv=EXCLUDED.naziv
                    RETURNING id
                    """,
                    (rec.region_name,),
                ).fetchone()

                conn.execute(
                    """
                    INSERT INTO geo_prefix (prefix, region_id, source)
                    VALUES (%s, %s, %s)
                    ON CONFLICT (prefix) DO UPDATE SET region_id=EXCLUDED.region_id, source=EXCLUDED.source
                    """,
                    (rec.prefix, region["id"], pdf_path.name),
                )

    print(f"Imported {len(records)} geo prefixes from {pdf_path}")


if __name__ == "__main__":
    main()

