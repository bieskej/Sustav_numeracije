-- Core schema for telecom numeration (Republika Srpska, geographic numbers only)

CREATE EXTENSION IF NOT EXISTS btree_gist;

CREATE TABLE IF NOT EXISTS operator (
  id BIGSERIAL PRIMARY KEY,
  naziv TEXT NOT NULL UNIQUE
);

CREATE TABLE IF NOT EXISTS region (
  id BIGSERIAL PRIMARY KEY,
  naziv TEXT NOT NULL UNIQUE,
  entitet TEXT NOT NULL DEFAULT 'Republika Srpska'
);

-- Geographic prefixes (e.g. 051) mapped to region
CREATE TABLE IF NOT EXISTS geo_prefix (
  prefix TEXT PRIMARY KEY,
  region_id BIGINT NOT NULL REFERENCES region(id) ON DELETE RESTRICT,
  source TEXT,
  created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TABLE IF NOT EXISTS opcine (
  id BIGSERIAL PRIMARY KEY,
  naziv TEXT NOT NULL UNIQUE,
  naziv_norm TEXT NOT NULL UNIQUE,
  created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TABLE IF NOT EXISTS lokacije (
  id BIGSERIAL PRIMARY KEY,
  opcina_id BIGINT NOT NULL REFERENCES opcine(id) ON DELETE CASCADE,
  naziv TEXT NOT NULL,
  naziv_norm TEXT NOT NULL,
  adresa TEXT,
  created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
  UNIQUE (opcina_id, naziv_norm)
);

CREATE TABLE IF NOT EXISTS uredjaji (
  id BIGSERIAL PRIMARY KEY,
  lokacija_id BIGINT NOT NULL REFERENCES lokacije(id) ON DELETE CASCADE,
  naziv TEXT NOT NULL,
  naziv_norm TEXT NOT NULL,
  tip TEXT NOT NULL CHECK (tip IN ('MSAN', 'GPON_OLT')),
  serijski_broj TEXT,
  aktivan BOOLEAN NOT NULL DEFAULT TRUE,
  created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
  UNIQUE (lokacija_id, naziv_norm)
);

-- Assigned blocks from regulator data (we store both types, but only import geografski)
CREATE TABLE IF NOT EXISTS dodijeljeni_blok (
  id BIGSERIAL PRIMARY KEY,
  operator_id BIGINT NOT NULL REFERENCES operator(id) ON DELETE RESTRICT,
  msisdn_od BIGINT NOT NULL,
  msisdn_do BIGINT NOT NULL,
  tip TEXT NOT NULL CHECK (tip IN ('geografski', 'mobilni')),
  created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
  CHECK (msisdn_od <= msisdn_do)
);

CREATE INDEX IF NOT EXISTS idx_dodijeljeni_blok_range ON dodijeljeni_blok (msisdn_od, msisdn_do);

CREATE TABLE IF NOT EXISTS postal_code (
  id BIGSERIAL PRIMARY KEY,
  opcina_id BIGINT NOT NULL REFERENCES opcine(id) ON DELETE CASCADE,
  postanski_broj TEXT NOT NULL,
  naziv_poste TEXT NOT NULL,
  created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
  UNIQUE (opcina_id, postanski_broj)
);

CREATE INDEX IF NOT EXISTS idx_postal_code_broj ON postal_code (postanski_broj);

CREATE TABLE IF NOT EXISTS rasponi_msisdn (
  id BIGSERIAL PRIMARY KEY,
  lokacija_id BIGINT NOT NULL REFERENCES lokacije(id) ON DELETE CASCADE,
  operator_id BIGINT REFERENCES operator(id) ON DELETE SET NULL,
  naziv TEXT,
  msisdn_od BIGINT NOT NULL,
  msisdn_do BIGINT NOT NULL,
  generirano BOOLEAN NOT NULL DEFAULT FALSE,
  created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
  CHECK (msisdn_od <= msisdn_do),
  msisdn_rng int8range GENERATED ALWAYS AS (int8range(msisdn_od, msisdn_do, '[]')) STORED
);

-- Hard constraint: no overlap between any ranges
ALTER TABLE rasponi_msisdn
  ADD CONSTRAINT rasponi_msisdn_no_overlap
  EXCLUDE USING gist (msisdn_rng WITH &&);

CREATE TABLE IF NOT EXISTS msisdn_brojevi (
  id BIGSERIAL PRIMARY KEY,
  raspon_id BIGINT NOT NULL REFERENCES rasponi_msisdn(id) ON DELETE CASCADE,
  msisdn BIGINT NOT NULL UNIQUE,
  status TEXT NOT NULL DEFAULT 'slobodan' CHECK (status IN ('slobodan','zauzet','karantena')),
  ime TEXT,
  prezime TEXT,
  oib TEXT CHECK (oib IS NULL OR (length(oib) = 11 AND oib ~ '^[0-9]{11}$')),
  datum_dodjele DATE,
  datum_karantene DATE,
  napomena TEXT,
  created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
  updated_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS idx_msisdn_raspon_status ON msisdn_brojevi (raspon_id, status);

CREATE OR REPLACE FUNCTION set_updated_at()
RETURNS TRIGGER AS $$
BEGIN
  NEW.updated_at = now();
  RETURN NEW;
END;
$$ LANGUAGE plpgsql;

DROP TRIGGER IF EXISTS tr_msisdn_updated_at ON msisdn_brojevi;
CREATE TRIGGER tr_msisdn_updated_at
BEFORE UPDATE ON msisdn_brojevi
FOR EACH ROW EXECUTE FUNCTION set_updated_at();

