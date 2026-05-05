from __future__ import annotations

import os
from pathlib import Path
from dotenv import load_dotenv

from app.core.database import Database, init_db
from app.utils.normalize import normalize_name


# NDC mapiranje - samo RS (50-59)
NDC_TO_OPCINA = {
    "50": "Mrkonjić Grad",
    "51": "Banja Luka",
    "52": "Prijedor",
    "53": "Doboj",
    "54": "Šamac",
    "55": "Bijeljina",
    "56": "Zvornik",
    "57": "Istočno Sarajevo",
    "58": "Foča",
    "59": "Trebinje",
}


def parse_csv(csv_path: Path) -> list[dict]:
    """Parse CSV i vrati samo HT Eronet blokove za RS (NDC 50-59)"""
    ht_blocks = []
    
    with open(csv_path, 'r', encoding='utf-8') as f:
        for i, line in enumerate(f, 1):
            if i == 1:  # Skip header
                continue
            parts = line.strip().split(';')
            if len(parts) < 5:
                continue
            
            service_type, ndc, blok, operator, length = parts[:5]
            
            # Filter: samo HT i samo RS (NDC 50-59)
            if "HT" in operator and ndc in NDC_TO_OPCINA:
                ht_blocks.append({
                    "service_type": service_type,
                    "ndc": ndc,
                    "blok": blok,
                    "operator": operator,
                    "length": int(length),
                })
    
    return ht_blocks


def generate_msisdn_range(ndc: str, blok: str, length: int) -> tuple[int, int]:
    """
    Generiši raspon MSISDN brojeva.
    Primjer: NDC=51, blok=5190, length=8
    - 51 (2) + 5190 (4) + 00 (2) = 515190 00 (8 cifara) → od 51519000 do 51519099
    """
    # Format: NDC + blok + vodeće nule za ostatak
    prefix = ndc + blok
    
    # Koliko cifara ostalaje za SN (subscriber number)
    remaining_digits = length - len(prefix)
    
    # Početak i kraj raspona
    start_suffix = "0" * remaining_digits
    end_suffix = "9" * remaining_digits
    
    msisdn_od = int(prefix + start_suffix)
    msisdn_do = int(prefix + end_suffix)
    
    return msisdn_od, msisdn_do


def main() -> None:
    load_dotenv()
    db_url = os.getenv("DATABASE_URL", "").strip()
    if not db_url:
        raise SystemExit("DATABASE_URL is required")

    csv_path = Path("deepseek_csv_20260504_e8f099.txt")
    if not csv_path.exists():
        raise SystemExit(f"CSV file not found: {csv_path}")

    ht_blocks = parse_csv(csv_path)
    if not ht_blocks:
        raise SystemExit("No HT Eronet blocks found for RS (NDC 50-59)")

    print(f"Found {len(ht_blocks)} HT Eronet blocks for RS:")
    for block in ht_blocks:
        print(f"  - NDC {block['ndc']}: {block['blok']} ({block['service_type']})")

    db = Database(db_url)
    init_db(db)

    with db.connect() as conn:
        with conn.transaction():
            # 0. Kreiraj/pronađi operatora
            operator = conn.execute(
                """
                INSERT INTO operator (naziv)
                VALUES ('HT d.d. Mostar')
                ON CONFLICT (naziv) DO UPDATE SET naziv=EXCLUDED.naziv
                RETURNING id
                """,
            ).fetchone()
            operator_id = operator["id"]

            # 1. Pripremi/kreira općine
            opcina_map = {}
            for ndc, opcina_naziv in NDC_TO_OPCINA.items():
                opcina_norm = normalize_name(opcina_naziv)
                result = conn.execute(
                    """
                    INSERT INTO opcine (naziv, naziv_norm)
                    VALUES (%s, %s)
                    ON CONFLICT (naziv_norm) DO NOTHING
                    RETURNING id
                    """,
                    (opcina_naziv, opcina_norm),
                ).fetchone()
                
                if result:
                    opcina_map[ndc] = result["id"]
                else:
                    # Ako nije kreirano (već postoji), pronađi ID
                    result = conn.execute(
                        "SELECT id FROM opcine WHERE naziv_norm=%s",
                        (opcina_norm,),
                    ).fetchone()
                    opcina_map[ndc] = result["id"]

            # 2. Za svaki HT blok, kreira raspon i generiši MSISDN brojeve
            imported_count = 0
            for block in ht_blocks:
                ndc = block["ndc"]
                opcina_id = opcina_map[ndc]
                opcina_naziv = NDC_TO_OPCINA[ndc]

                # Kreiraj/pronađi lokaciju (za sada jednu po općini)
                lokacija_naziv = f"Lokacija {opcina_naziv}"
                lokacija_norm = normalize_name(lokacija_naziv)
                
                lokacija = conn.execute(
                    """
                    INSERT INTO lokacije (opcina_id, naziv, naziv_norm, adresa)
                    VALUES (%s, %s, %s, %s)
                    ON CONFLICT (opcina_id, naziv_norm) DO NOTHING
                    RETURNING id
                    """,
                    (opcina_id, lokacija_naziv, lokacija_norm, opcina_naziv),
                ).fetchone()
                
                if not lokacija:
                    lokacija = conn.execute(
                        "SELECT id FROM lokacije WHERE opcina_id=%s AND naziv_norm=%s",
                        (opcina_id, lokacija_norm),
                    ).fetchone()
                
                lokacija_id = lokacija["id"]

                # Generiši raspon
                msisdn_od, msisdn_do = generate_msisdn_range(
                    ndc, block["blok"], block["length"]
                )

                # Kreiraj raspon
                raspon = conn.execute(
                    """
                    INSERT INTO rasponi_msisdn (lokacija_id, operator_id, naziv, msisdn_od, msisdn_do, generirano)
                    VALUES (%s, %s, %s, %s, %s, false)
                    RETURNING id
                    """,
                    (
                        lokacija_id,
                        operator_id,
                        f"HT {opcina_naziv} - NDC {ndc} Blok {block['blok']}",
                        msisdn_od,
                        msisdn_do,
                    ),
                ).fetchone()

                raspon_id = raspon["id"]

                # Generiši sve MSISDN brojeve za ovaj raspon
                num_count = msisdn_do - msisdn_od + 1
                print(f"  Generating {num_count} numbers for NDC {ndc} blok {block['blok']}...")
                
                for i in range(num_count):
                    msisdn = msisdn_od + i
                    conn.execute(
                        """
                        INSERT INTO msisdn_brojevi (raspon_id, msisdn, status)
                        VALUES (%s, %s, 'slobodan')
                        """,
                        (raspon_id, msisdn),
                    )
                
                # Označi raspon kao generirano
                conn.execute(
                    "UPDATE rasponi_msisdn SET generirano=true WHERE id=%s",
                    (raspon_id,),
                )
                
                imported_count += 1

    print(f"\nSuccessfully imported {imported_count} HT Eronet blocks for RS")
    print(f"Total MSISDN numbers generated: {sum(b['length'] - len(b['ndc'] + b['blok']) for b in ht_blocks) * 10}")


if __name__ == "__main__":
    main()
