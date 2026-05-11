from __future__ import annotations

"""Import HT Eronet MSISDN blocks from the official RAK Excel file.

Source: Dodijeljeni blokovi brojeva_h 18-2-2026.xlsx
        (RAK – Regulatorna agencija za komunikacije BiH)

NDC→municipality mapping follows Plan brojeva za telefonske usluge u BiH
(primjena 01.10.2017., source: 8e85c57b-fd57-4bf0-b0cf-4efae2f1bf09.pdf).
"""

import os
from pathlib import Path

from dotenv import load_dotenv
from psycopg.errors import ExclusionViolation

from app.core.database import Database, init_db
from app.utils.ndc_map import NDC_TO_MUNICIPALITY
from app.utils.normalize import normalize_name


def parse_xlsx(xlsx_path: Path) -> list[dict]:
    """Read all HT d.d. Mostar blocks from the RAK Excel allocation file.

    Excel structure (row 7 = header, data starts row 14):
      Col A: NDC  (merged cells – carries down)
      Col B: Blok
      Col C: Max N(S)N length
      Col D: Min N(S)N length
      Col E: Telekom operator
      Col F: Dodatne informacije
    """
    try:
        import openpyxl
    except ImportError:
        raise SystemExit("openpyxl is required: pip install openpyxl")

    wb = openpyxl.load_workbook(xlsx_path, data_only=True)
    ws = wb.active

    blocks: list[dict] = []
    current_ndc: int | None = None
    in_mobile_section = False

    for row in ws.iter_rows(min_row=14, values_only=True):
        # Column A carries NDC (merged cells – only set on first row of group)
        if row[0] is not None:
            current_ndc = row[0]

        blok = row[1]
        if blok is None or current_ndc is None:
            continue

        max_len = row[2]
        min_len = row[3]
        operator = str(row[4] or "").strip()
        info = str(row[5] or "").strip()

        # Only import HT d.d. Mostar blocks
        if "HT" not in operator:
            continue

        length = max_len if max_len is not None else min_len
        if not isinstance(length, int):
            try:
                length = int(length)
            except (TypeError, ValueError):
                continue

        # Determine service type: mobile section header in Excel reads
        # "MOBILNI TELEFONSKI SERVISI" in col A
        ndc_str = str(current_ndc)
        is_mobile = ndc_str in ("63", "64")

        blocks.append(
            {
                "service_type": "Mobilni" if is_mobile else "Fiksni",
                "ndc": ndc_str,
                "blok": str(blok),
                "operator": operator,
                "length": length,
            }
        )

    return blocks


def generate_msisdn_range(blok: str, length: int) -> tuple[int, int]:
    """Calculate msisdn_od / msisdn_do for a given block + N(S)N length.

    The blok value from the RAK Excel already includes the NDC as its leading
    digits (e.g., NDC=30, blok=3049 → prefix "3049", range 30490000–30499999).
    """
    remaining = length - len(blok)
    if remaining < 0:
        raise ValueError(f"Blok '{blok}' duži od dužine {length}")
    return int(blok + "0" * remaining), int(blok + "9" * remaining)


def main() -> None:
    load_dotenv()
    db_url = os.getenv("DATABASE_URL", "").strip()
    if not db_url:
        raise SystemExit("DATABASE_URL is required")

    xlsx_path = Path("Dodijeljeni blokovi brojeva_h 18-2-2026.xlsx")
    if not xlsx_path.exists():
        raise SystemExit(f"Excel file not found: {xlsx_path}")

    blocks = parse_xlsx(xlsx_path)
    if not blocks:
        raise SystemExit("No HT Eronet blocks found in Excel file")

    print(f"Pronađeno {len(blocks)} HT Eronet blokova u Excel datoteci")

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

                try:
                    msisdn_od, msisdn_do = generate_msisdn_range(block["blok"], block["length"])
                except ValueError as e:
                    print(f"  Preskočeno NDC {ndc} blok {block['blok']}: {e}")
                    skipped_unknown += 1
                    continue

                tip = "mobilni" if block["service_type"] == "Mobilni" else "geografski"

                # Use savepoint so ExclusionViolation doesn't abort the outer transaction
                try:
                    with conn.transaction():
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
                        raspon = conn.execute(
                            """
                            INSERT INTO rasponi_msisdn (lokacija_id, operator_id, naziv, msisdn_od, msisdn_do, generirano)
                            VALUES (%s, %s, %s, %s, %s, false)
                            RETURNING id
                            """,
                            (lokacija_id, operator_id, naziv, msisdn_od, msisdn_do),
                        ).fetchone()

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

                except ExclusionViolation:
                    print(f"  Preskočeno (overlap): NDC {ndc} blok {block['blok']}")
                    skipped_overlap += 1

    total_numbers = sum(
        10 ** (b["length"] - len(b["blok"]))
        for b in blocks
        if NDC_TO_MUNICIPALITY.get(b["ndc"]) and b["length"] > len(b["blok"])
    )
    print(f"\nUvezeno raspona:           {imported}")
    print(f"Preskočeno (overlap):      {skipped_overlap}")
    print(f"Preskočeno (nepoznati NDC): {skipped_unknown}")
    print(f"Ukupno generiranih MSISDN: ~{total_numbers:,}")


if __name__ == "__main__":
    main()
