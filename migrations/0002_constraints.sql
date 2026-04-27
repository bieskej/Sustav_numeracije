-- Extra uniqueness to keep imports idempotent

DO $$
BEGIN
  IF NOT EXISTS (
    SELECT 1 FROM pg_indexes WHERE schemaname = 'public' AND indexname = 'ux_dodijeljeni_blok_tuple'
  ) THEN
    CREATE UNIQUE INDEX ux_dodijeljeni_blok_tuple
      ON dodijeljeni_blok (operator_id, msisdn_od, msisdn_do, tip);
  END IF;
END $$;

