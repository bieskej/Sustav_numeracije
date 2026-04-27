from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, field_validator
from typing import Optional
import sqlite3

app = FastAPI(title="MSISDN Numeracija API", version="1.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

DB_PATH = "numeracija.db"

def get_db():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    return conn

def init_db():
    conn = get_db()
    conn.executescript("""
        CREATE TABLE IF NOT EXISTS opcine (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            naziv TEXT NOT NULL UNIQUE,
            zip_code TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );
        CREATE TABLE IF NOT EXISTS lokacije (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            opcina_id INTEGER NOT NULL REFERENCES opcine(id) ON DELETE CASCADE,
            naziv TEXT NOT NULL,
            adresa TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );
        CREATE TABLE IF NOT EXISTS uredjaji (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            lokacija_id INTEGER NOT NULL REFERENCES lokacije(id) ON DELETE CASCADE,
            naziv TEXT NOT NULL,
            tip TEXT NOT NULL CHECK(tip IN ('MSAN','GPON_OLT')),
            serijski_broj TEXT,
            aktivan INTEGER NOT NULL DEFAULT 1,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );
        CREATE TABLE IF NOT EXISTS rasponi_msisdn (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            lokacija_id INTEGER NOT NULL REFERENCES lokacije(id) ON DELETE CASCADE,
            naziv TEXT,
            msisdn_od TEXT NOT NULL,
            msisdn_do TEXT NOT NULL,
            generirano INTEGER NOT NULL DEFAULT 0,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );
        CREATE TABLE IF NOT EXISTS msisdn_brojevi (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            raspon_id INTEGER NOT NULL REFERENCES rasponi_msisdn(id) ON DELETE CASCADE,
            msisdn TEXT NOT NULL UNIQUE,
            status TEXT NOT NULL DEFAULT 'slobodan' CHECK(status IN ('slobodan','zauzet','karantena')),
            ime TEXT,
            prezime TEXT,
            oib TEXT CHECK(oib IS NULL OR (length(oib)=11 AND oib GLOB '[0-9]*')),
            datum_dodjele TEXT,
            datum_karantene TEXT,
            napomena TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );
        CREATE TRIGGER IF NOT EXISTS update_msisdn_ts
        AFTER UPDATE ON msisdn_brojevi
        BEGIN
            UPDATE msisdn_brojevi SET updated_at=CURRENT_TIMESTAMP WHERE id=NEW.id;
        END;
    """)
    try:
        conn.execute("INSERT INTO opcine (naziv, zip_code) VALUES ('Zagreb','10000')")
        conn.execute("INSERT INTO opcine (naziv, zip_code) VALUES ('Split','21000')")
        conn.execute("INSERT INTO lokacije (opcina_id,naziv,adresa) VALUES (1,'Centar Zagreb','Ilica 1')")
        conn.execute("INSERT INTO lokacije (opcina_id,naziv,adresa) VALUES (1,'Novi Zagreb','Dugave 5')")
        conn.execute("INSERT INTO lokacije (opcina_id,naziv,adresa) VALUES (2,'Split Centar','Marmontova 3')")
        conn.execute("INSERT INTO uredjaji (lokacija_id,naziv,tip,serijski_broj) VALUES (1,'MSAN-ZG-01','MSAN','SN001')")
        conn.execute("INSERT INTO uredjaji (lokacija_id,naziv,tip,serijski_broj) VALUES (1,'OLT-ZG-01','GPON_OLT','SN002')")
        conn.execute("INSERT INTO uredjaji (lokacija_id,naziv,tip,serijski_broj) VALUES (2,'MSAN-NZ-01','MSAN','SN003')")
        conn.commit()
    except Exception:
        conn.rollback()
    conn.close()

init_db()

# ── MODELI ────────────────────────────────────────────────────────────────────

class OpcinaIn(BaseModel):
    naziv: str
    zip_code: Optional[str] = None

class LokacijaIn(BaseModel):
    opcina_id: int
    naziv: str
    adresa: Optional[str] = None

class UredajIn(BaseModel):
    lokacija_id: int
    naziv: str
    tip: str
    serijski_broj: Optional[str] = None
    aktivan: int = 1

class RasponIn(BaseModel):
    lokacija_id: int
    naziv: Optional[str] = None
    msisdn_od: str
    msisdn_do: str

    @field_validator('msisdn_od','msisdn_do')
    @classmethod
    def samo_brojevi(cls, v):
        if not v.isdigit():
            raise ValueError('Mora sadržavati samo znamenke')
        return v

class MsisdnUpdateIn(BaseModel):
    status: str
    ime: Optional[str] = None
    prezime: Optional[str] = None
    oib: Optional[str] = None
    datum_dodjele: Optional[str] = None
    datum_karantene: Optional[str] = None
    napomena: Optional[str] = None

    @field_validator('oib')
    @classmethod
    def oib_check(cls, v):
        if v and (len(v) != 11 or not v.isdigit()):
            raise ValueError('OIB mora imati točno 11 znamenki')
        return v

class MsisdnCreateIn(BaseModel):
    raspon_id: int
    msisdn: str

# ── OPĆINE ────────────────────────────────────────────────────────────────────

@app.get("/opcine")
def list_opcine():
    db = get_db()
    rows = db.execute("""
        SELECT o.*, COUNT(l.id) as broj_lokacija
        FROM opcine o LEFT JOIN lokacije l ON l.opcina_id=o.id
        GROUP BY o.id ORDER BY o.naziv
    """).fetchall()
    db.close(); return [dict(r) for r in rows]

@app.get("/opcine/{id}")
def get_opcina(id: int):
    db = get_db()
    r = db.execute("SELECT * FROM opcine WHERE id=?", (id,)).fetchone()
    db.close()
    if not r: raise HTTPException(404,"Općina nije pronađena")
    return dict(r)

@app.post("/opcine", status_code=201)
def create_opcina(data: OpcinaIn):
    db = get_db()
    try:
        c = db.execute("INSERT INTO opcine (naziv,zip_code) VALUES (?,?)", (data.naziv,data.zip_code))
        db.commit()
        r = db.execute("SELECT * FROM opcine WHERE id=?", (c.lastrowid,)).fetchone()
        return dict(r)
    except sqlite3.IntegrityError: raise HTTPException(400,"Naziv već postoji")
    finally: db.close()

@app.put("/opcine/{id}")
def update_opcina(id: int, data: OpcinaIn):
    db = get_db()
    try:
        r = db.execute("UPDATE opcine SET naziv=?,zip_code=? WHERE id=?", (data.naziv,data.zip_code,id))
        db.commit()
        if r.rowcount==0: raise HTTPException(404,"Općina nije pronađena")
        return dict(db.execute("SELECT * FROM opcine WHERE id=?", (id,)).fetchone())
    except sqlite3.IntegrityError: raise HTTPException(400,"Naziv već postoji")
    finally: db.close()

@app.delete("/opcine/{id}", status_code=204)
def delete_opcina(id: int):
    db = get_db()
    r = db.execute("DELETE FROM opcine WHERE id=?", (id,))
    db.commit(); db.close()
    if r.rowcount==0: raise HTTPException(404,"Općina nije pronađena")

# ── LOKACIJE ──────────────────────────────────────────────────────────────────

@app.get("/lokacije")
def list_lokacije(opcina_id: Optional[int]=None):
    db = get_db()
    w = "WHERE l.opcina_id=?" if opcina_id else ""
    p = (opcina_id,) if opcina_id else ()
    rows = db.execute(f"""
        SELECT l.*, o.naziv as opcina_naziv,
               COUNT(DISTINCT u.id) as broj_uredjaja,
               COUNT(DISTINCT rm.id) as broj_raspona
        FROM lokacije l
        JOIN opcine o ON o.id=l.opcina_id
        LEFT JOIN uredjaji u ON u.lokacija_id=l.id
        LEFT JOIN rasponi_msisdn rm ON rm.lokacija_id=l.id
        {w} GROUP BY l.id ORDER BY o.naziv,l.naziv
    """, p).fetchall()
    db.close(); return [dict(r) for r in rows]

@app.get("/lokacije/{id}")
def get_lokacija(id: int):
    db = get_db()
    r = db.execute("""
        SELECT l.*, o.naziv as opcina_naziv FROM lokacije l
        JOIN opcine o ON o.id=l.opcina_id WHERE l.id=?
    """, (id,)).fetchone()
    db.close()
    if not r: raise HTTPException(404,"Lokacija nije pronađena")
    return dict(r)

@app.post("/lokacije", status_code=201)
def create_lokacija(data: LokacijaIn):
    db = get_db()
    try:
        c = db.execute("INSERT INTO lokacije (opcina_id,naziv,adresa) VALUES (?,?,?)",
                       (data.opcina_id,data.naziv,data.adresa))
        db.commit()
        r = db.execute("""SELECT l.*, o.naziv as opcina_naziv FROM lokacije l
                          JOIN opcine o ON o.id=l.opcina_id WHERE l.id=?""", (c.lastrowid,)).fetchone()
        return dict(r)
    except sqlite3.IntegrityError as e: raise HTTPException(400,str(e))
    finally: db.close()

@app.put("/lokacije/{id}")
def update_lokacija(id: int, data: LokacijaIn):
    db = get_db()
    r = db.execute("UPDATE lokacije SET opcina_id=?,naziv=?,adresa=? WHERE id=?",
                   (data.opcina_id,data.naziv,data.adresa,id))
    db.commit()
    if r.rowcount==0: db.close(); raise HTTPException(404,"Lokacija nije pronađena")
    row = db.execute("""SELECT l.*, o.naziv as opcina_naziv FROM lokacije l
                        JOIN opcine o ON o.id=l.opcina_id WHERE l.id=?""", (id,)).fetchone()
    db.close(); return dict(row)

@app.delete("/lokacije/{id}", status_code=204)
def delete_lokacija(id: int):
    db = get_db()
    r = db.execute("DELETE FROM lokacije WHERE id=?", (id,))
    db.commit(); db.close()
    if r.rowcount==0: raise HTTPException(404,"Lokacija nije pronađena")

# ── UREĐAJI ───────────────────────────────────────────────────────────────────

@app.get("/uredjaji")
def list_uredjaji(lokacija_id: Optional[int]=None):
    db = get_db()
    w = "WHERE u.lokacija_id=?" if lokacija_id else ""
    p = (lokacija_id,) if lokacija_id else ()
    rows = db.execute(f"""
        SELECT u.*, l.naziv as lokacija_naziv, o.naziv as opcina_naziv
        FROM uredjaji u JOIN lokacije l ON l.id=u.lokacija_id
        JOIN opcine o ON o.id=l.opcina_id {w} ORDER BY o.naziv,l.naziv,u.naziv
    """, p).fetchall()
    db.close(); return [dict(r) for r in rows]

@app.get("/uredjaji/{id}")
def get_uredjaj(id: int):
    db = get_db()
    r = db.execute("""
        SELECT u.*, l.naziv as lokacija_naziv, o.naziv as opcina_naziv
        FROM uredjaji u JOIN lokacije l ON l.id=u.lokacija_id
        JOIN opcine o ON o.id=l.opcina_id WHERE u.id=?
    """, (id,)).fetchone()
    db.close()
    if not r: raise HTTPException(404,"Uređaj nije pronađen")
    return dict(r)

@app.post("/uredjaji", status_code=201)
def create_uredjaj(data: UredajIn):
    db = get_db()
    try:
        c = db.execute("INSERT INTO uredjaji (lokacija_id,naziv,tip,serijski_broj,aktivan) VALUES (?,?,?,?,?)",
                       (data.lokacija_id,data.naziv,data.tip,data.serijski_broj,data.aktivan))
        db.commit()
        r = db.execute("""SELECT u.*, l.naziv as lokacija_naziv, o.naziv as opcina_naziv
                          FROM uredjaji u JOIN lokacije l ON l.id=u.lokacija_id
                          JOIN opcine o ON o.id=l.opcina_id WHERE u.id=?""", (c.lastrowid,)).fetchone()
        return dict(r)
    except sqlite3.IntegrityError as e: raise HTTPException(400,str(e))
    finally: db.close()

@app.put("/uredjaji/{id}")
def update_uredjaj(id: int, data: UredajIn):
    db = get_db()
    r = db.execute("UPDATE uredjaji SET lokacija_id=?,naziv=?,tip=?,serijski_broj=?,aktivan=? WHERE id=?",
                   (data.lokacija_id,data.naziv,data.tip,data.serijski_broj,data.aktivan,id))
    db.commit()
    if r.rowcount==0: db.close(); raise HTTPException(404,"Uređaj nije pronađen")
    row = db.execute("""SELECT u.*, l.naziv as lokacija_naziv, o.naziv as opcina_naziv
                        FROM uredjaji u JOIN lokacije l ON l.id=u.lokacija_id
                        JOIN opcine o ON o.id=l.opcina_id WHERE u.id=?""", (id,)).fetchone()
    db.close(); return dict(row)

@app.delete("/uredjaji/{id}", status_code=204)
def delete_uredjaj(id: int):
    db = get_db()
    r = db.execute("DELETE FROM uredjaji WHERE id=?", (id,))
    db.commit(); db.close()
    if r.rowcount==0: raise HTTPException(404,"Uređaj nije pronađen")

# ── RASPONI ───────────────────────────────────────────────────────────────────

@app.get("/rasponi")
def list_rasponi(lokacija_id: Optional[int]=None):
    db = get_db()
    w = "WHERE r.lokacija_id=?" if lokacija_id else ""
    p = (lokacija_id,) if lokacija_id else ()
    rows = db.execute(f"""
        SELECT r.*, l.naziv as lokacija_naziv, o.naziv as opcina_naziv,
               COUNT(m.id) as ukupno,
               SUM(CASE WHEN m.status='slobodan' THEN 1 ELSE 0 END) as slobodni,
               SUM(CASE WHEN m.status='zauzet' THEN 1 ELSE 0 END) as zauzeti,
               SUM(CASE WHEN m.status='karantena' THEN 1 ELSE 0 END) as karantena
        FROM rasponi_msisdn r
        JOIN lokacije l ON l.id=r.lokacija_id
        JOIN opcine o ON o.id=l.opcina_id
        LEFT JOIN msisdn_brojevi m ON m.raspon_id=r.id
        {w} GROUP BY r.id ORDER BY r.msisdn_od
    """, p).fetchall()
    db.close(); return [dict(r) for r in rows]

@app.get("/rasponi/{id}")
def get_raspon(id: int):
    db = get_db()
    r = db.execute("""
        SELECT r.*, l.naziv as lokacija_naziv, o.naziv as opcina_naziv
        FROM rasponi_msisdn r JOIN lokacije l ON l.id=r.lokacija_id
        JOIN opcine o ON o.id=l.opcina_id WHERE r.id=?
    """, (id,)).fetchone()
    db.close()
    if not r: raise HTTPException(404,"Raspon nije pronađen")
    return dict(r)

def check_raspon_overlap(db, msisdn_od: str, msisdn_do: str, exclude_id: int = None):
    """
    Provjera preklapanja s bilo kojim postojećim rasponom.
    Dva raspona se preklapaju ako: novi_od <= postojeci_do AND novi_do >= postojeci_od
    """
    query = """
        SELECT r.id, r.msisdn_od, r.msisdn_do, l.naziv as lokacija_naziv, o.naziv as opcina_naziv
        FROM rasponi_msisdn r
        JOIN lokacije l ON l.id = r.lokacija_id
        JOIN opcine o ON o.id = l.opcina_id
        WHERE CAST(r.msisdn_od AS INTEGER) <= CAST(? AS INTEGER)
          AND CAST(r.msisdn_do AS INTEGER) >= CAST(? AS INTEGER)
    """
    params = [msisdn_do, msisdn_od]
    if exclude_id:
        query += " AND r.id != ?"
        params.append(exclude_id)
    conflicts = db.execute(query, params).fetchall()
    if conflicts:
        details = ", ".join(
            f"{c['msisdn_od']}–{c['msisdn_do']} ({c['lokacija_naziv']}, {c['opcina_naziv']})"
            for c in conflicts
        )
        raise HTTPException(
            400,
            f"Raspon se preklapa s postojećim rasponom/ima: {details}"
        )

@app.post("/rasponi", status_code=201)
def create_raspon(data: RasponIn):
    if int(data.msisdn_od) >= int(data.msisdn_do):
        raise HTTPException(400,"msisdn_od mora biti manji od msisdn_do")
    db = get_db()
    try:
        check_raspon_overlap(db, data.msisdn_od, data.msisdn_do)
        c = db.execute("INSERT INTO rasponi_msisdn (lokacija_id,naziv,msisdn_od,msisdn_do) VALUES (?,?,?,?)",
                       (data.lokacija_id,data.naziv,data.msisdn_od,data.msisdn_do))
        db.commit()
        r = db.execute("""
            SELECT r.*, l.naziv as lokacija_naziv, o.naziv as opcina_naziv,
                   0 as ukupno, 0 as slobodni, 0 as zauzeti, 0 as karantena
            FROM rasponi_msisdn r JOIN lokacije l ON l.id=r.lokacija_id
            JOIN opcine o ON o.id=l.opcina_id WHERE r.id=?
        """, (c.lastrowid,)).fetchone()
        return dict(r)
    except sqlite3.IntegrityError as e: raise HTTPException(400,str(e))
    finally: db.close()

@app.put("/rasponi/{id}")
def update_raspon(id: int, data: RasponIn):
    if int(data.msisdn_od) >= int(data.msisdn_do):
        raise HTTPException(400,"msisdn_od mora biti manji od msisdn_do")
    db = get_db()
    check_raspon_overlap(db, data.msisdn_od, data.msisdn_do, exclude_id=id)
    r = db.execute("UPDATE rasponi_msisdn SET lokacija_id=?,naziv=?,msisdn_od=?,msisdn_do=? WHERE id=?",
                   (data.lokacija_id,data.naziv,data.msisdn_od,data.msisdn_do,id))
    db.commit()
    if r.rowcount==0: db.close(); raise HTTPException(404,"Raspon nije pronađen")
    row = db.execute("""SELECT r.*, l.naziv as lokacija_naziv, o.naziv as opcina_naziv
                        FROM rasponi_msisdn r JOIN lokacije l ON l.id=r.lokacija_id
                        JOIN opcine o ON o.id=l.opcina_id WHERE r.id=?""", (id,)).fetchone()
    db.close(); return dict(row)

@app.delete("/rasponi/{id}", status_code=204)
def delete_raspon(id: int):
    db = get_db()
    r = db.execute("DELETE FROM rasponi_msisdn WHERE id=?", (id,))
    db.commit(); db.close()
    if r.rowcount==0: raise HTTPException(404,"Raspon nije pronađen")

@app.post("/rasponi/{id}/generiraj", status_code=201)
def generiraj_brojeve(id: int):
    db = get_db()
    raspon = db.execute("SELECT * FROM rasponi_msisdn WHERE id=?", (id,)).fetchone()
    if not raspon: db.close(); raise HTTPException(404,"Raspon nije pronađen")
    if raspon["generirano"]: db.close(); raise HTTPException(400,"Već generirano")
    od, do = int(raspon["msisdn_od"]), int(raspon["msisdn_do"])
    if do - od > 100000: db.close(); raise HTTPException(400,"Max 100.000 brojeva po generiranju")
    db.executemany("INSERT OR IGNORE INTO msisdn_brojevi (raspon_id,msisdn) VALUES (?,?)",
                   [(id, str(n)) for n in range(od, do+1)])
    db.execute("UPDATE rasponi_msisdn SET generirano=1 WHERE id=?", (id,))
    db.commit(); count = do - od + 1; db.close()
    return {"poruka": f"Generirano {count} MSISDN brojeva", "count": count}

# ── MSISDN BROJEVI ────────────────────────────────────────────────────────────

@app.get("/msisdn")
def list_msisdn(
    raspon_id: Optional[int]=None,
    status: Optional[str]=None,
    search: Optional[str]=None,
    page: int=Query(1,ge=1),
    per_page: int=Query(50,ge=1,le=500)
):
    db = get_db()
    where, params = ["1=1"], []
    if raspon_id: where.append("m.raspon_id=?"); params.append(raspon_id)
    if status: where.append("m.status=?"); params.append(status)
    if search:
        where.append("(m.msisdn LIKE ? OR m.ime LIKE ? OR m.prezime LIKE ? OR m.oib LIKE ?)")
        s = f"%{search}%"; params.extend([s,s,s,s])
    ws = " AND ".join(where)
    total = db.execute(f"SELECT COUNT(*) FROM msisdn_brojevi m WHERE {ws}", params).fetchone()[0]
    offset = (page-1)*per_page
    rows = db.execute(f"""
        SELECT m.*, r.msisdn_od, r.msisdn_do, l.naziv as lokacija_naziv, o.naziv as opcina_naziv
        FROM msisdn_brojevi m
        JOIN rasponi_msisdn r ON r.id=m.raspon_id
        JOIN lokacije l ON l.id=r.lokacija_id
        JOIN opcine o ON o.id=l.opcina_id
        WHERE {ws} ORDER BY m.msisdn LIMIT ? OFFSET ?
    """, params+[per_page,offset]).fetchall()
    db.close()
    return {"total":total,"page":page,"per_page":per_page,
            "pages":(total+per_page-1)//per_page,"data":[dict(r) for r in rows]}

@app.get("/msisdn/{id}")
def get_msisdn(id: int):
    db = get_db()
    r = db.execute("""
        SELECT m.*, l.naziv as lokacija_naziv, o.naziv as opcina_naziv
        FROM msisdn_brojevi m JOIN rasponi_msisdn r ON r.id=m.raspon_id
        JOIN lokacije l ON l.id=r.lokacija_id JOIN opcine o ON o.id=l.opcina_id
        WHERE m.id=?
    """, (id,)).fetchone()
    db.close()
    if not r: raise HTTPException(404,"MSISDN nije pronađen")
    return dict(r)

@app.post("/msisdn", status_code=201)
def create_msisdn(data: MsisdnCreateIn):
    db = get_db()
    try:
        c = db.execute("INSERT INTO msisdn_brojevi (raspon_id,msisdn) VALUES (?,?)",
                       (data.raspon_id,data.msisdn))
        db.commit()
        r = db.execute("SELECT * FROM msisdn_brojevi WHERE id=?", (c.lastrowid,)).fetchone()
        return dict(r)
    except sqlite3.IntegrityError: raise HTTPException(400,"MSISDN već postoji")
    finally: db.close()

@app.put("/msisdn/{id}")
def update_msisdn(id: int, data: MsisdnUpdateIn):
    db = get_db()
    if not db.execute("SELECT 1 FROM msisdn_brojevi WHERE id=?", (id,)).fetchone():
        db.close(); raise HTTPException(404,"MSISDN nije pronađen")
    if data.status == "slobodan":
        db.execute("""UPDATE msisdn_brojevi SET status=?,ime=NULL,prezime=NULL,oib=NULL,
                      datum_dodjele=NULL,datum_karantene=NULL,napomena=? WHERE id=?""",
                   (data.status,data.napomena,id))
    else:
        db.execute("""UPDATE msisdn_brojevi SET status=?,ime=?,prezime=?,oib=?,
                      datum_dodjele=?,datum_karantene=?,napomena=? WHERE id=?""",
                   (data.status,data.ime,data.prezime,data.oib,
                    data.datum_dodjele,data.datum_karantene,data.napomena,id))
    db.commit()
    r = db.execute("""SELECT m.*, l.naziv as lokacija_naziv, o.naziv as opcina_naziv
                      FROM msisdn_brojevi m JOIN rasponi_msisdn rs ON rs.id=m.raspon_id
                      JOIN lokacije l ON l.id=rs.lokacija_id JOIN opcine o ON o.id=l.opcina_id
                      WHERE m.id=?""", (id,)).fetchone()
    db.close(); return dict(r)

@app.delete("/msisdn/{id}", status_code=204)
def delete_msisdn(id: int):
    db = get_db()
    r = db.execute("DELETE FROM msisdn_brojevi WHERE id=?", (id,))
    db.commit(); db.close()
    if r.rowcount==0: raise HTTPException(404,"MSISDN nije pronađen")

# ── STATISTIKE ────────────────────────────────────────────────────────────────

@app.get("/statistike")
def get_statistike():
    db = get_db()
    def q(sql): return db.execute(sql).fetchone()[0]
    stats = {
        "opcine": q("SELECT COUNT(*) FROM opcine"),
        "lokacije": q("SELECT COUNT(*) FROM lokacije"),
        "uredjaji": q("SELECT COUNT(*) FROM uredjaji"),
        "rasponi": q("SELECT COUNT(*) FROM rasponi_msisdn"),
        "ukupno_msisdn": q("SELECT COUNT(*) FROM msisdn_brojevi"),
        "slobodni": q("SELECT COUNT(*) FROM msisdn_brojevi WHERE status='slobodan'"),
        "zauzeti": q("SELECT COUNT(*) FROM msisdn_brojevi WHERE status='zauzet'"),
        "karantena": q("SELECT COUNT(*) FROM msisdn_brojevi WHERE status='karantena'"),
    }
    db.close(); return stats
