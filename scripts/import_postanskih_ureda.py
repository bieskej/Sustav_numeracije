from __future__ import annotations

import os
from pathlib import Path
from dotenv import load_dotenv

from app.core.database import Database, init_db
from app.utils.normalize import normalize_name


# Poštanski brojevi za Banju Luku (NDC 51) - prema Plan numeracije
BANJA_LUKA_POSTAL_CODES = {
    "78101": "Pošta Banja Luka - centar",
    "78000": "Pošta Banjaluka",
    "78101": "Pošta Banja Luka centralna",
}

NDC_TO_OPCINA = {
    "51": "Banja Luka",
}


def main() -> None:
    load_dotenv()
    db_url = os.getenv("DATABASE_URL", "").strip()
    if not db_url:
        raise SystemExit("DATABASE_URL is required")

    db = Database(db_url)
    init_db(db)

    with db.connect() as conn:
        with conn.transaction():
            # 1. Pronađi opcinu Banja Luka
            opcina = conn.execute(
                "SELECT id FROM opcine WHERE naziv_norm=%s",
                (normalize_name("Banja Luka"),),
            ).fetchone()
            
            if not opcina:
                print("Opcina 'Banja Luka' nije pronađena. Trebam prvo importovati blokove.")
                return
            
            opcina_id = opcina["id"]
            
            # 2. Pronađi lokaciju za Banju Luku
            lokacija = conn.execute(
                "SELECT id FROM lokacije WHERE opcina_id=%s LIMIT 1",
                (opcina_id,),
            ).fetchone()
            
            if not lokacija:
                print("Lokacija za opcinu nije pronađena.")
                return
            
            lokacija_id = lokacija["id"]
            
            # 3. Ubaci poštanske brojeve
            imported_count = 0
            for postal_code, naziv_poste in BANJA_LUKA_POSTAL_CODES.items():
                result = conn.execute(
                    """
                    INSERT INTO postal_code (opcina_id, postanski_broj, naziv_poste, default_lokacija_id)
                    VALUES (%s, %s, %s, %s)
                    ON CONFLICT (opcina_id, postanski_broj) DO UPDATE 
                    SET naziv_poste=EXCLUDED.naziv_poste, default_lokacija_id=EXCLUDED.default_lokacija_id
                    RETURNING id
                    """,
                    (opcina_id, postal_code, naziv_poste, lokacija_id),
                ).fetchone()
                
                if result:
                    imported_count += 1
                    print(f"  {postal_code}: {naziv_poste}")

    print(f"\nSuccessfully imported {imported_count} postal codes for Banja Luka")


if __name__ == "__main__":
    main()
