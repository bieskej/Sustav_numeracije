-- MVP changes: regions for opcine, default location for postal codes, assignment events

-- Add region_id to opcine
ALTER TABLE opcine ADD COLUMN region_id BIGINT REFERENCES region(id) ON DELETE RESTRICT;

-- Add default_lokacija_id to postal_code
ALTER TABLE postal_code ADD COLUMN default_lokacija_id BIGINT REFERENCES lokacije(id) ON DELETE SET NULL;

-- Create assignment_event table
CREATE TABLE IF NOT EXISTS assignment_event (
  id BIGSERIAL PRIMARY KEY,
  action TEXT NOT NULL CHECK (action IN ('allocated', 'released', 'quarantine')),
  msisdn BIGINT NOT NULL,
  raspon_id BIGINT NOT NULL REFERENCES rasponi_msisdn(id) ON DELETE CASCADE,
  lokacija_id BIGINT NOT NULL REFERENCES lokacije(id) ON DELETE CASCADE,
  postal_code TEXT,
  ime TEXT,
  prezime TEXT,
  oib TEXT,
  napomena TEXT,
  timestamp TIMESTAMPTZ NOT NULL DEFAULT now()
);

-- Index for efficient queries
CREATE INDEX IF NOT EXISTS idx_assignment_event_timestamp ON assignment_event (timestamp);
CREATE INDEX IF NOT EXISTS idx_assignment_event_msisdn ON assignment_event (msisdn);
CREATE INDEX IF NOT EXISTS idx_assignment_event_lokacija ON assignment_event (lokacija_id);