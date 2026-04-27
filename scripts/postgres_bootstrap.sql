-- Run this file as a PostgreSQL superuser, for example:
--   psql -U postgres -d postgres -f scripts/postgres_bootstrap.sql
--
-- CREATE DATABASE cannot run inside a DO block, so we use psql's \gexec
-- to execute the statement only when the database is missing.

SELECT 'CREATE DATABASE numeracija OWNER admin_user'
WHERE NOT EXISTS (
  SELECT 1
  FROM pg_database
  WHERE datname = 'numeracija'
)\gexec

\connect numeracija

ALTER DATABASE numeracija OWNER TO admin_user;
ALTER SCHEMA public OWNER TO admin_user;
GRANT ALL ON SCHEMA public TO admin_user;
GRANT ALL PRIVILEGES ON DATABASE numeracija TO admin_user;
