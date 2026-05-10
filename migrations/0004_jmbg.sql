-- Rename oib -> jmbg in msisdn_brojevi and assignment_event
-- JMBG (Jedinstveni matični broj građana) is the BiH/Yugoslav personal ID: 13 digits with module-11 checksum

DO $$
BEGIN
  IF EXISTS (
    SELECT 1 FROM information_schema.columns
    WHERE table_name = 'msisdn_brojevi' AND column_name = 'oib'
  ) THEN
    ALTER TABLE msisdn_brojevi RENAME COLUMN oib TO jmbg;
  END IF;

  ALTER TABLE msisdn_brojevi DROP CONSTRAINT IF EXISTS msisdn_brojevi_oib_check;

  IF NOT EXISTS (
    SELECT 1 FROM pg_constraint WHERE conname = 'msisdn_brojevi_jmbg_check'
  ) THEN
    ALTER TABLE msisdn_brojevi ADD CONSTRAINT msisdn_brojevi_jmbg_check
      CHECK (jmbg IS NULL OR (length(jmbg) = 13 AND jmbg ~ '^[0-9]{13}$'));
  END IF;

  IF EXISTS (
    SELECT 1 FROM information_schema.columns
    WHERE table_name = 'assignment_event' AND column_name = 'oib'
  ) THEN
    ALTER TABLE assignment_event RENAME COLUMN oib TO jmbg;
  END IF;
END $$;
