# 📡 MSISDN Numeracija — Upute za pokretanje

## Struktura projekta
```
telefon/
├── backend/
│   ├── main.py          ← FastAPI REST API
│   └── requirements.txt
└── frontend/
    └── index.html       ← Vanilla JS sučelje
```

## 1. Pokretanje backenda (PostgreSQL)

```bash
cd backend

# Instaliraj ovisnosti
pip install -r requirements.txt

# Postavi DATABASE_URL (primjer)
# PowerShell:
#   $env:DATABASE_URL="postgresql://user:pass@localhost:5432/numeracija"
#
# Pokreni server (nova modularna aplikacija)
uvicorn app.main:app --reload --port 8000
```

API dokumentacija dostupna na: http://localhost:8000/docs

## 2. Pokretanje frontenda

Otvori `frontend/index.html` u browseru.

> Ili pokreni lokalni HTTP server:
> ```bash
> cd frontend
> python -m http.server 3000
> ```
> Zatim otvori: http://localhost:3000

---

## REST API Endpoints

### Općine
| Metoda | URL | Opis |
|--------|-----|------|
| GET | /opcine | Lista svih općina |
| GET | /opcine/{id} | Detalji općine |
| POST | /opcine | Kreiranje |
| PUT | /opcine/{id} | Uređivanje |
| DELETE | /opcine/{id} | Brisanje |

### Lokacije
| Metoda | URL | Opis |
|--------|-----|------|
| GET | /lokacije?opcina_id= | Lista (filter po općini) |
| POST | /lokacije | Kreiranje |
| PUT | /lokacije/{id} | Uređivanje |
| DELETE | /lokacije/{id} | Brisanje |

### Uređaji (MSAN / GPON OLT)
| Metoda | URL | Opis |
|--------|-----|------|
| GET | /uredjaji?lokacija_id= | Lista |
| POST | /uredjaji | Kreiranje |
| PUT | /uredjaji/{id} | Uređivanje |
| DELETE | /uredjaji/{id} | Brisanje |

### Rasponi MSISDN
| Metoda | URL | Opis |
|--------|-----|------|
| GET | /rasponi?lokacija_id= | Lista |
| POST | /rasponi | Kreiranje raspona |
| PUT | /rasponi/{id} | Uređivanje |
| DELETE | /rasponi/{id} | Brisanje |
| POST | /rasponi/{id}/generiraj | Generiranje svih brojeva u rasponu |

### MSISDN Brojevi
| Metoda | URL | Opis |
|--------|-----|------|
| GET | /msisdn | Lista (filter + paginacija) |
| GET | /msisdn?raspon_id=&status=&search=&page=&per_page= | Filtrirani prikaz |
| POST | /msisdn | Dodavanje pojedinog broja |
| PUT | /msisdn/{id} | Ažuriranje statusa/korisnika |
| DELETE | /msisdn/{id} | Brisanje |

### Statistike
| Metoda | URL | Opis |
|--------|-----|------|
| GET | /statistike | Pregled svih brojeva po statusu |

---

## Statusi MSISDN broja
- 🟢 **slobodan** — broj nije dodijeljen
- 🔴 **zauzet** — broj je dodijeljen korisniku (ime, prezime, OIB)
- 🟡 **karantena** — broj je bio zauzet, čeka period prije ponovne dodjele

## Napomene
- PostgreSQL shema se automatski inicijalizira iz `migrations/*.sql` pri prvom pokretanju
- Max 100.000 MSISDN brojeva po jednoj operaciji generiranja
- OIB validacija: točno 11 znamenki
