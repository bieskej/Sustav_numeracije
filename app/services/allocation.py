from __future__ import annotations

from psycopg import Connection

from app.models.assignment import AllocationIn, AllocationOut
from app.crud import assignment_event as crud_event


def get_lokacija_from_raspon(conn: Connection, raspon_id: int) -> int:
    row = conn.execute("SELECT lokacija_id FROM rasponi_msisdn WHERE id = %s", (raspon_id,)).fetchone()
    return row["lokacija_id"] if row else None


def allocate_number(conn: Connection, data: AllocationIn) -> AllocationOut:
    # 1. Resolve postal_code to default_lokacija_id
    postal_row = conn.execute(
        """
        SELECT p.default_lokacija_id, l.naziv AS lokacija_naziv, o.naziv AS opcina_naziv, r.naziv AS region_naziv
        FROM postal_code p
        JOIN lokacije l ON l.id = p.default_lokacija_id
        JOIN opcine o ON o.id = p.opcina_id
        JOIN region r ON r.id = o.region_id
        WHERE p.postanski_broj = %s
        """,
        (data.postal_code,),
    ).fetchone()
    if not postal_row:
        raise ValueError("Poštanski broj nije pronađen")
    if not postal_row["default_lokacija_id"]:
        raise ValueError("Poštanski broj nema konfigurisanu default lokaciju")

    lokacija_id = postal_row["default_lokacija_id"]
    lokacija_naziv = postal_row["lokacija_naziv"]
    opcina_naziv = postal_row["opcina_naziv"]
    region_naziv = postal_row["region_naziv"]

    # 2. Find the first allocatable rasponi_msisdn for that location, ordered by msisdn_od
    raspon_row = conn.execute(
        """
        SELECT r.id, r.msisdn_od, r.msisdn_do
        FROM rasponi_msisdn r
        WHERE r.lokacija_id = %s AND r.generirano = true
        ORDER BY r.msisdn_od
        LIMIT 1
        """,
        (lokacija_id,),
    ).fetchone()
    if not raspon_row:
        raise ValueError("Nema dostupnih raspona za ovu lokaciju")

    raspon_id = raspon_row["id"]

    # 3. Atomically claim the lowest slobodan MSISDN in that range
    msisdn_row = conn.execute(
        """
        SELECT m.id, m.msisdn
        FROM msisdn_brojevi m
        WHERE m.raspon_id = %s AND m.status = 'slobodan'
        ORDER BY m.msisdn
        LIMIT 1
        FOR UPDATE
        """,
        (raspon_id,),
    ).fetchone()
    if not msisdn_row:
        raise ValueError("Nema slobodnih brojeva u rasponu")

    msisdn_id = msisdn_row["id"]
    msisdn = msisdn_row["msisdn"]

    # Mark as zauzet
    conn.execute(
        """
        UPDATE msisdn_brojevi
        SET status = 'zauzet', ime = %s, prezime = %s, jmbg = %s, napomena = %s, datum_dodjele = CURRENT_DATE
        WHERE id = %s
        """,
        (data.ime, data.prezime, data.jmbg, data.napomena, msisdn_id),
    )

    # 4. Log assignment event
    crud_event.create_assignment_event(
        conn,
        action="allocated",
        msisdn=msisdn,
        raspon_id=raspon_id,
        lokacija_id=lokacija_id,
        postal_code=data.postal_code,
        ime=data.ime,
        prezime=data.prezime,
        jmbg=data.jmbg,
        napomena=data.napomena,
    )

    return AllocationOut(
        msisdn=msisdn,
        lokacija_id=lokacija_id,
        lokacija_naziv=lokacija_naziv,
        opcina_naziv=opcina_naziv,
        region_naziv=region_naziv,
    )
