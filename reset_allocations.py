from app.core.database import Database

db = Database('postgresql://admin_user:admin_lozinka@localhost:5432/numeracija')
with db.connect() as conn:
    with conn.transaction():
        count = conn.execute("""
            UPDATE msisdn_brojevi 
            SET status='slobodan', ime=NULL, prezime=NULL, oib=NULL, datum_dodjele=NULL, datum_karantene=NULL
            WHERE status='zauzet'
        """).rowcount
        print(f'✓ Resetovano {count} brojeva')
