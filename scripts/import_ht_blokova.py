from __future__ import annotations

import os
from pathlib import Path

from dotenv import load_dotenv
from psycopg.errors import ExclusionViolation

from app.core.database import Database, init_db
from app.utils.ndc_map import NDC_TO_MUNICIPALITY
from app.utils.normalize import normalize_name


def parse_csv(csv_path: Path) -> list[dict]:
    """Parse CSV and return all HT Eronet blocks (FBiH + RS + mobile)."""
    blocks = []
    with open(csv_path, "r", encoding="utf-8-sig") as f:
        for i, line in enumerate(f, 1):
            if i == 1:
                continue
            parts = line.strip().split(";")
            if len(parts) < 5:
                continue
            service_type, ndc, blok, operator, length_str = parts[:5]
            if "HT" not in operator:
                continue
            try:
                length = int(length_str.strip())
            except ValueError:
                continue
            blocks.append(
                {
                    "service_type": service_type.strip(),
                    "ndc": ndc.strip(),
                    "blok": blok.strip(),
                    "operator": operator.strip(),
                    "length": length,
                }
            )
    return blocks


def generate_msisdn_range(ndc: str, blok: str, length: int) -> tuple[int, int]:
    """Calculate msisdn_od / msisdn_do for a given NDC + block + N(S)N length."""
    prefix = ndc + blok
    remaining = length - len(prefix)
    if remaining < 0:
        raise ValueError(f"Prefix '{prefix}' duži od dužine {length}")
    return int(prefix + "0" * remaining), int(prefix + "9" * remaining)


def main() -> None:
    load_dotenv()
    db_url = os.getenv("DATABASE_URL", "").strip()
    if not db_url:
        raise SystemExit("DATABASE_URL is required")

    csv_path = Path("deepseek_csv_20260504_e8f099.txt")
    if not csv_path.exists():
        raise SystemExit(f"CSV file not found: {csv_path}")

    blocks = parse_csv(csv_path)
    if not blocks:
        raise SystemExit("No HT Eronet blocks found in CSV")

    print(f"Found {len(blocks)} HT Eronet blocks")

    db = Database(db_url)
    init_db(db)

    with db.connect() as conn:
        with conn.transaction():
            # 1. Upsert all needed regions
            region_id_map: dict[str, int] = {}
            seen_entiteti = {v[1] for v in NDC_TO_MUNICIPALITY.values()}
            for entitet in seen_entiteti:
                row = conn.execute(
                    "INSERT INTO region (naziv, entitet) VALUES (%s, %s) ON CONFLICT (naziv) DO NOTHING RETURNING id",
                    (entitet, entitet),
                ).fetchone()
                if row:
                    region_id_map[entitet] = row["id"]
                else:
                    region_id_map[entitet] = conn.execute(
                        "SELECT id FROM region WHERE naziv=%s", (entitet,)
                    ).fetchone()["id"]

            # 2. Upsert operator
            operator_row = conn.execute(
                "INSERT INTO operator (naziv) VALUES ('HT d.d. Mostar') ON CONFLICT (naziv) DO UPDATE SET naziv=EXCLUDED.naziv RETURNING id"
            ).fetchone()
            ht_dd_id = operator_row["id"]

            operator_row2 = conn.execute(
                "INSERT INTO operator (naziv) VALUES ('HT d.o.o. Mostar') ON CONFLICT (naziv) DO UPDATE SET naziv=EXCLUDED.naziv RETURNING id"
            ).fetchone()
            ht_doo_id = operator_row2["id"]

            # 3. Import each block
            imported = 0
            skipped_overlap = 0
            skipped_unknown = 0

            for block in blocks:
                ndc = block["ndc"]
                municipality_info = NDC_TO_MUNICIPALITY.get(ndc)
                if not municipality_info:
                    print(f"  Preskočeno: nepoznati NDC {ndc}")
                    skipped_unknown += 1
                    continue

                opcina_naziv, entitet = municipality_info
                region_id = region_id_map[entitet]

                # Opcina
                opcina_norm = normalize_name(opcina_naziv)
                opcina = conn.execute(
                    "INSERT INTO opcine (naziv, naziv_norm, region_id) VALUES (%s, %s, %s) ON CONFLICT (naziv_norm) DO NOTHING RETURNING id",
                    (opcina_naziv, opcina_norm, region_id),
                ).fetchone()
                if not opcina:
                    opcina = conn.execute(
                        "SELECT id FROM opcine WHERE naziv_norm=%s", (opcina_norm,)
                    ).fetchone()
                opcina_id = opcina["id"]

                # Lokacija (one per municipality)
                lokacija_naziv = f"Lokacija {opcina_naziv}"
                lokacija_norm = normalize_name(lokacija_naziv)
                lokacija = conn.execute(
                    "INSERT INTO lokacije (opcina_id, naziv, naziv_norm) VALUES (%s, %s, %s) ON CONFLICT (opcina_id, naziv_norm) DO NOTHING RETURNING id",
                    (opcina_id, lokacija_naziv, lokacija_norm),
                ).fetchone()
                if not lokacija:
                    lokacija = conn.execute(
                        "SELECT id FROM lokacije WHERE opcina_id=%s AND naziv_norm=%s",
                        (opcina_id, lokacija_norm),
                    ).fetchone()
                lokacija_id = lokacija["id"]

                # Operator id
                operator_id = ht_doo_id if "d.o.o" in block["operator"] else ht_dd_id

                # Range
                try:
                    msisdn_od, msisdn_do = generate_msisdn_range(ndc, block["blok"], block["length"])
                except ValueError as e:
                    print(f"  Preskočeno NDC {ndc} blok {block['blok']}: {e}")
                    skipped_unknown += 1
                    continue

                tip = "mobilni" if "mobil" in block["service_type"].lower() else "geografski"

                # Insert into dodijeljeni_blok (regulatory record)
                conn.execute(
                    """
                    INSERT INTO dodijeljeni_blok (operator_id, msisdn_od, msisdn_do, tip)
                    VALUES (%s, %s, %s, %s)
                    ON CONFLICT (operator_id, msisdn_od, msisdn_do, tip) DO NOTHING
                    """,
                    (operator_id, msisdn_od, msisdn_do, tip),
                )

                # Create raspon_msisdn (operational range)
                naziv = f"HT {opcina_naziv} - NDC {ndc} Blok {block['blok']}"
                try:
                    raspon = conn.execute(
                        """
                        INSERT INTO rasponi_msisdn (lokacija_id, operator_id, naziv, msisdn_od, msisdn_do, generirano)
                        VALUES (%s, %s, %s, %s, %s, false)
                        RETURNING id
                        """,
                        (lokacija_id, operator_id, naziv, msisdn_od, msisdn_do),
                    ).fetchone()
                except ExclusionViolation:
                    print(f"  Preskočeno (overlap): NDC {ndc} blok {block['blok']}")
                    skipped_overlap += 1
                    continue

                raspon_id = raspon["id"]
                num_count = msisdn_do - msisdn_od + 1
                print(f"  Generiranje {num_count} brojeva: NDC {ndc} blok {block['blok']} ({opcina_naziv})")

                conn.execute(
                    """
                    INSERT INTO msisdn_brojevi (raspon_id, msisdn)
                    SELECT %s, gs FROM generate_series(%s, %s) AS gs
                    ON CONFLICT (msisdn) DO NOTHING
                    """,
                    (raspon_id, msisdn_od, msisdn_do),
                )
                conn.execute(
                    "UPDATE rasponi_msisdn SET generirano=true WHERE id=%s", (raspon_id,)
                )
                imported += 1

    total_numbers = sum(
        10 ** (b["length"] - len(b["ndc"] + b["blok"]))
        for b in blocks
        if NDC_TO_MUNICIPALITY.get(b["ndc"]) and b["length"] > len(b["ndc"] + b["blok"])
    )
    print(f"\nUvezeno raspona: {imported}")
    print(f"Preskočeno (overlap): {skipped_overlap}")
    print(f"Preskočeno (nepoznati NDC): {skipped_unknown}")
    print(f"Ukupno generiranih MSISDN: ~{total_numbers:,}")


if __name__ == "__main__":
    main()
