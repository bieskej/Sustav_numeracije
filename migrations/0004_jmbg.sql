-- Rename oib -> jmbg in msisdn_brojevi and assignment_event
-- JMBG (Jedinstveni matični broj građana) is the BiH/Yugoslav personal ID: 13 digits with module-11 checksum

ALTER TABLE msisdn_brojevi RENAME COLUMN oib TO jmbg;

ALTER TABLE msisdn_brojevi
  DROP CONSTRAINT IF EXISTS msisdn_brojevi_oib_check,
  ADD CONSTRAINT msisdn_brojevi_jmbg_check
    CHECK (jmbg IS NULL OR (length(jmbg) = 13 AND jmbg ~ '^[0-9]{13}$'));

ALTER TABLE assignment_event RENAME COLUMN oib TO jmbg;
