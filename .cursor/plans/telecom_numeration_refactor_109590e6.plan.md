---
name: Telecom numeration refactor
overview: Refactor the current monolithic SQLite FastAPI app into a production-ready, modular FastAPI backend targeting PostgreSQL, with strict geographic MSISDN rules, non-overlapping ranges, operator/block ingestion from Excel, and RS-only postal/region data ingestion from checked-in inputs.
todos:
  - id: inspect_existing_backend
    content: Scan existing backend folder for other modules/assets and confirm current runtime entrypoints (only main.py/requirements found so far).
    status: completed
  - id: design_postgres_schema
    content: "Draft Postgres schema + migration strategy: BIGINT MSISDN, exclusion constraint for non-overlap, new tables (operator, dodijeljeni_blok, region, postal_code, geo_prefix)."
    status: completed
  - id: module_split
    content: Define exact module boundaries and function signatures for core/db, crud, services, api routers, and pydantic schemas.
    status: completed
  - id: import_pipelines
    content: Specify deterministic import scripts for Plan numeracije PDF, Excel blocks (geographical only), and RS postal codes (scrape + normalize + upsert).
    status: completed
  - id: api_contracts
    content: Define endpoint set, filters, pagination, and statistics payloads for all resources including operators and postal codes.
    status: completed
isProject: false
---

## Current state (what we’re refactoring)
- Existing app is a single file at [c:\Telekom\backend\main.py](c:\Telekom\backend\main.py) using **SQLite (`sqlite3`) + raw SQL**.
- Tables already present: `opcine` → `lokacije` → `uredjaji` and `rasponi_msisdn` → `msisdn_brojevi`.
- Business logic already exists for:
  - range overlap check (`check_raspon_overlap`) and generation endpoint (`/rasponi/{id}/generiraj`)
  - msisdn status lifecycle (`slobodan|zauzet|karantena`)
  - filtering/pagination on `/msisdn`.

## Target architecture (modular FastAPI)
We will create a new Python package under `app/` and keep responsibilities separated:
- [app/main.py](app/main.py): FastAPI app factory, middleware, router includes.
- [app/core/database.py](app/core/database.py): PostgreSQL connection management, `get_db()` dependency, `init_db()` bootstrap.
- `app/models/`: **Pydantic-only** request/response schemas (no ORM).
  - [app/models/opcina.py](app/models/opcina.py)
  - [app/models/lokacija.py](app/models/lokacija.py)
  - [app/models/uredjaj.py](app/models/uredjaj.py)
  - [app/models/raspon.py](app/models/raspon.py)
  - [app/models/msisdn.py](app/models/msisdn.py)
  - [app/models/operator.py](app/models/operator.py)
  - [app/models/postal.py](app/models/postal.py)
  - [app/models/region.py](app/models/region.py)
- `app/crud/`: **SQL-only** query functions (no business rules).
  - Each module exposes functions like `list_*`, `get_*`, `create_*`, `update_*`, `delete_*`, plus stats queries.
- `app/services/`: business logic and validation.
  - `check_raspon_overlap(...)` generalized for Postgres and operator/type constraints
  - `generate_msisdn(...)` (bulk insert, idempotent, size guard)
  - MSISDN validation: digits-only, length, allowed prefixes from regulation PDF
  - normalization utilities (municipality naming, whitespace/case, diacritics folding)
- `app/api/`: FastAPI routers, request validation, pagination/filter wiring.
- `app/utils/`: parsing helpers, importer utilities, text normalization.

## Database design (PostgreSQL) and constraints
We will implement the schema as SQL migrations (simple, deterministic) and enforce constraints at the DB level where possible.

### Keep and adjust existing entities
- `opcine` (municipalities): ensure unique normalized name.
- `lokacije` (locations): FK to `opcine`.
- `uredjaji` (devices): FK to `lokacije`; `tip` constrained to `MSAN|GPON_OLT`.
- `rasponi_msisdn` (ranges): FK to `lokacije` and **new FK to `operator`**.
- `msisdn_brojevi` (numbers): FK to `rasponi_msisdn`; unique `msisdn`.

### New tables (as requested)
- `operator`
  - `id`, `naziv` (unique)
- `dodijeljeni_blok`
  - `id`, `operator_id` (FK), `msisdn_od`, `msisdn_do`, `tip` (`geografski|mobilni`)
  - index on (`msisdn_od`,`msisdn_do`), and **service-level rule**: only import `tip='geografski'`.
- `region`
  - `id`, `naziv` (unique), `entitet` (constant default `'Republika Srpska'`)
- `postal_code`
  - `id`, `opcina_id` (FK), `postanski_broj`, `naziv_poste`
  - unique (`opcina_id`,`postanski_broj`) and index on `postanski_broj`.

### Non-overlapping ranges (hard constraint)
PostgreSQL can enforce this robustly with range types + exclusion constraints.
- Store `msisdn_od`/`msisdn_do` as **BIGINT** (not TEXT).
- Add generated `int8range` (or store a range column) and use an **EXCLUDE constraint** to prevent overlap.
- Scope: overlap must be prevented at least globally for all geographic MSISDN ranges; optionally we can scope it by `tip` or by prefix class.

### MSISDN validity + “geographical only”
- Enforce digits-only and plausible length in services/Pydantic.
- Enforce allowed prefixes from the regulation PDF via a `prefix` reference dataset:
  - Create a small table `geo_prefix` (or `prefix_rule`) mapping `prefix` → `region_id` (+ metadata).
  - Service validation: reject MSISDN whose leading digits don’t match any allowed geographic prefix.

## Imports / data pipelines
### 1) Regulation PDF: prefix extraction
Inputs checked into repo under `inputs/`:
- [inputs/Plan numeracije.pdf](inputs/Plan numeracije.pdf)

Implementation:
- Build a parser in `app/utils/plan_numeracije_parser.py`:
  - Extract candidate prefixes (e.g. `051`) and associated region/area names.
  - Persist to `region` + `geo_prefix` tables.
- Provide a CLI script:
  - `scripts/import_plan_numeracije.py` (reads PDF, upserts regions/prefixes).

### 2) Excel: Dodijeljeni blokovi brojeva
Inputs:
- [inputs/Dodijeljeni blokovi brojeva.xlsx](inputs/Dodijeljeni blokovi brojeva.xlsx)

Implementation:
- `app/utils/excel_blocks_parser.py`:
  - Parse rows, normalize operator names, map to `operator` table.
  - Filter only `tip='geografski'`.
  - Store into `dodijeljeni_blok`.
- `scripts/import_dodijeljeni_blokovi.py` for repeatable import (idempotent upsert strategy).

### 3) Postal codes (RS only)
Sources (scraped at import time, then cached in DB):
- `https://xn--potanske-brojeve-med.cybo.com/bosna-i-hercegovina/republika-srpska/#listcodes`
- `https://bs.wikipedia.org/wiki/Spisak_po%C5%A1tanskih_brojeva_u_Bosni_i_Hercegovini`

Implementation:
- `app/utils/postal_scrape.py`:
  - Pull and parse municipality/post office/postal code tuples.
  - Normalize municipality names to match `opcine` via deterministic normalization + fuzzy fallback.
  - Insert/update `postal_code` for matched municipalities only.
- `scripts/import_postal_codes_rs.py`.

## API endpoints (routers)
Create routers in `app/api/` mirroring current endpoints plus new entities:
- `/opcine`, `/lokacije`, `/uredjaji`, `/rasponi`, `/msisdn` (ported from current app)
- `/operatori`, `/postal-codes` (new)

Features:
- CRUD
- filtering + pagination (standard pattern: `page`, `per_page`, plus entity filters)
- statistics endpoints:
  - keep `/statistike` and add operator/range distribution stats.

## Step-by-step refactor approach (low risk)
1. **Introduce `app/` package** and move FastAPI construction + middleware into `app/main.py`.
2. **Implement Postgres DB layer** in [app/core/database.py](app/core/database.py) with env-driven DSN.
3. **Create SQL migrations** under `migrations/` and an `init_db()` that applies them sequentially (tracking in `schema_migrations` table).
4. **Port Pydantic schemas** from monolith into `app/models/*`.
5. **Port existing CRUD SQL** into `app/crud/*` (same queries adapted for Postgres + BIGINT MSISDN).
6. **Port services** (`check_raspon_overlap`, `generate_msisdn`, msisdn validation) into `app/services/*`.
7. **Add new tables + endpoints** for operators, assigned blocks, regions/prefixes, postal codes.
8. **Add import scripts** for PDF/Excel/postal sites.
9. **Tighten constraints** (exclusion constraint, unique indexes) and add consistent error mapping to HTTP errors.
10. **Smoke-test endpoints** locally with `uvicorn` and sample imports.

## Runtime/config
- `DATABASE_URL` required (Postgres DSN).
- CORS remains configurable (default permissive for dev).
- Keep development convenience commands in README.

## Suggested directory additions (beyond your requested tree)
- `migrations/` for SQL migration files.
- `scripts/` for importers (PDF/Excel/postal).
- `inputs/` committed for deterministic parsing (per your choice).