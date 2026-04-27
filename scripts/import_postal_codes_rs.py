from __future__ import annotations

import json
import os
from pathlib import Path

from dotenv import load_dotenv

from app.core.database import Database, init_db
from app.utils.normalize import normalize_name
from app.utils.postal_pdf_parser import parse_spisak_posta_pdf


def load_postal_mapping(mapping_path: Path) -> dict:
    if not mapping_path.exists():
        raise SystemExit(f"Mapping file not found: {mapping_path}")
    with open(mapping_path, 'r', encoding='utf-8') as f:
        return json.load(f)


def main() -> None:
    load_dotenv()
    db_url = os.getenv("DATABASE_URL", "").strip()
    if not db_url:
        raise SystemExit("DATABASE_URL is required")

    db = Database(db_url)
    init_db(db)

    candidates = [
        "inputs/Spisak-posta.pdf",
        "inputs/spisak-posta.pdf",
        "Spisak-posta.pdf",
        "spisak-posta.pdf",
    ]
    pdf_path = next((p for p in candidates if Path(p).exists()), None)
    if not pdf_path:
        raise SystemExit("Missing Spisak-posta.pdf. Expected one of: " + ", ".join(candidates))

    mapping_path = Path("inputs/postal_mapping.json")
    mapping = load_postal_mapping(mapping_path)

    records = parse_spisak_posta_pdf(Path(pdf_path))
    if not records:
        raise SystemExit("No postal records parsed from PDF (format may have changed).")

    # Build mapping dict
    postal_to_muni = {m["postal_office"]: (m["municipality"], m["region"]) for m in mapping["mappings"]}
    default_region = mapping["defaults"]["region"]

    with db.connect() as conn:
        regions = conn.execute("SELECT id, naziv FROM region").fetchall()
        region_by_name = {r["naziv"]: r["id"] for r in regions}

        opcine = conn.execute("SELECT id, naziv, naziv_norm, region_id FROM opcine").fetchall()
        opc_by_norm = {(o["naziv_norm"], o["region_id"]): o for o in opcine}

        inserted = 0
        unmatched = []

        with conn.transaction():
            for r in records:
                # Map postal office to municipality and region
                if r.naziv_poste in postal_to_muni:
                    muni_name, reg_name = postal_to_muni[r.naziv_poste]
                else:
                    unmatched.append(r.naziv_poste)
                    continue

                reg_id = region_by_name.get(reg_name)
                if not reg_id:
                    # Insert region if missing
                    reg_row = conn.execute(
                        "INSERT INTO region (naziv, entitet) VALUES (%s, %s) RETURNING id",
                        (reg_name, reg_name),
                    ).fetchone()
                    reg_id = reg_row["id"]
                    region_by_name[reg_name] = reg_id

                norm_muni = normalize_name(muni_name)
                opc = opc_by_norm.get((norm_muni, reg_id))
                if not opc:
                    # Insert opcina if missing
                    opc_row = conn.execute(
                        "INSERT INTO opcine (naziv, naziv_norm, region_id) VALUES (%s, %s, %s) RETURNING id",
                        (muni_name, norm_muni, reg_id),
                    ).fetchone()
                    opc_id = opc_row["id"]
                    opc_by_norm[(norm_muni, reg_id)] = {"id": opc_id}
                else:
                    opc_id = opc["id"]

                conn.execute(
                    """
                    INSERT INTO postal_code (opcina_id, postanski_broj, naziv_poste)
                    VALUES (%s, %s, %s)
                    ON CONFLICT (opcina_id, postanski_broj) DO UPDATE SET naziv_poste=EXCLUDED.naziv_poste
                    """,
                    (opc_id, r.postanski_broj, r.naziv_poste),
                )
                inserted += 1

        if unmatched:
            raise SystemExit(f"Unmatched postal offices: {', '.join(unmatched)}")

        print(f"Inserted/updated {inserted} postal codes.")


if __name__ == "__main__":
    main()