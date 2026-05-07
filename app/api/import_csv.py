from __future__ import annotations

import csv
import io

from fastapi import APIRouter, Depends, HTTPException, UploadFile, File
from psycopg import Connection

from app.api.deps import db_dep
from app.services.raspon_service import RangeOverlapError, create_range, generate_msisdn
from app.utils.ndc_map import NDC_TO_MUNICIPALITY
from app.utils.normalize import normalize_name


router = APIRouter(prefix="/import", tags=["import"])


def _upsert_region(conn: Connection, naziv: str, entitet: str) -> int:
    row = conn.execute(
        "INSERT INTO region (naziv, entitet) VALUES (%s, %s) ON CONFLICT (naziv) DO NOTHING RETURNING id",
        (naziv, entitet),
    ).fetchone()
    if row:
        return row["id"]
    return conn.execute("SELECT id FROM region WHERE naziv=%s", (naziv,)).fetchone()["id"]


def _upsert_opcina(conn: Connection, naziv: str, region_id: int) -> int:
    norm = normalize_name(naziv)
    row = conn.execute(
        "INSERT INTO opcine (naziv, naziv_norm, region_id) VALUES (%s, %s, %s) ON CONFLICT (naziv_norm) DO NOTHING RETURNING id",
        (naziv, norm, region_id),
    ).fetchone()
    if row:
        return row["id"]
    return conn.execute("SELECT id FROM opcine WHERE naziv_norm=%s", (norm,)).fetchone()["id"]


def _upsert_lokacija(conn: Connection, opcina_id: int, naziv: str) -> int:
    norm = normalize_name(naziv)
    row = conn.execute(
        "INSERT INTO lokacije (opcina_id, naziv, naziv_norm) VALUES (%s, %s, %s) ON CONFLICT (opcina_id, naziv_norm) DO NOTHING RETURNING id",
        (opcina_id, naziv, norm),
    ).fetchone()
    if row:
        return row["id"]
    return conn.execute(
        "SELECT id FROM lokacije WHERE opcina_id=%s AND naziv_norm=%s", (opcina_id, norm)
    ).fetchone()["id"]


def _upsert_operator(conn: Connection, naziv: str) -> int:
    row = conn.execute(
        "INSERT INTO operator (naziv) VALUES (%s) ON CONFLICT (naziv) DO UPDATE SET naziv=EXCLUDED.naziv RETURNING id",
        (naziv,),
    ).fetchone()
    return row["id"]


@router.post("/csv-rak")
async def import_csv_rak(
    file: UploadFile = File(...),
    conn: Connection = Depends(db_dep),
):
    content = await file.read()
    try:
        text = content.decode("utf-8-sig")
    except UnicodeDecodeError:
        text = content.decode("latin-1")

    first_line = text.split("\n")[0]
    delimiter = ";" if ";" in first_line else ","

    reader = csv.DictReader(io.StringIO(text), delimiter=delimiter)

    # Normalise header keys (strip whitespace)
    raw_rows = []
    for row in reader:
        raw_rows.append({k.strip(): (v or "").strip() for k, v in row.items()})

    if not raw_rows:
        raise HTTPException(400, "CSV datoteka je prazna ili nema zaglavlja")

    imported = 0
    skipped = 0
    errors: list[str] = []

    for i, row in enumerate(raw_rows, start=2):
        operator_name = row.get("Operator", "")
        if "HT" not in operator_name:
            skipped += 1
            continue

        dodijeljeno = row.get("Dodijeljeno", "DA").upper()
        if dodijeljeno == "NE":
            skipped += 1
            continue

        ndc = row.get("NDC", "").strip()
        blok = row.get("Blok", "").strip()
        vrsta = row.get("Vrsta usluge", "Fiksni").strip()

        # Dužina column may appear under different names
        duzina_raw = (
            row.get("Dužina broja (N(S)N)")
            or row.get("Duzina broja (N(S)N)")
            or row.get("Dužina")
            or row.get("Duzina")
            or "8"
        ).strip()
        try:
            length = int(duzina_raw)
        except ValueError:
            skipped += 1
            errors.append(f"Red {i}: nevažeća dužina '{duzina_raw}'")
            continue

        if not ndc or not blok:
            skipped += 1
            continue

        # blok already includes the NDC as its leading digits
        prefix = blok
        remaining = length - len(prefix)
        if remaining < 0:
            skipped += 1
            errors.append(f"Red {i}: blok '{blok}' duži od dužine {length}")
            continue

        msisdn_od = int(prefix + "0" * remaining)
        msisdn_do = int(prefix + "9" * remaining)
        tip = "mobilni" if "mobil" in vrsta.lower() else "geografski"

        municipality_info = NDC_TO_MUNICIPALITY.get(ndc)
        if not municipality_info:
            skipped += 1
            errors.append(f"Red {i}: nepoznati NDC '{ndc}'")
            continue

        opcina_naziv, entitet = municipality_info

        try:
            with conn.transaction():
                region_id = _upsert_region(conn, entitet, entitet)
                opcina_id = _upsert_opcina(conn, opcina_naziv, region_id)
                lokacija_naziv = f"Lokacija {opcina_naziv}"
                lokacija_id = _upsert_lokacija(conn, opcina_id, lokacija_naziv)
                operator_id = _upsert_operator(conn, operator_name)

                raspon = create_range(
                    conn,
                    lokacija_id=lokacija_id,
                    operator_id=operator_id,
                    naziv=f"HT {opcina_naziv} - NDC {ndc} Blok {blok}",
                    msisdn_od=msisdn_od,
                    msisdn_do=msisdn_do,
                )
                generate_msisdn(conn, raspon_id=raspon["id"])
        except RangeOverlapError:
            skipped += 1
            continue
        except Exception as exc:
            skipped += 1
            errors.append(f"Red {i}: {exc}")
            continue

        imported += 1

    return {"imported": imported, "skipped": skipped, "errors": errors[:20]}
