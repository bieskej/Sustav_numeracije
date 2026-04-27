from __future__ import annotations

import psycopg


ADMIN_DSN = "postgresql://admin_user:admin_lozinka@localhost:5432/postgres"
TARGET_DB = "numeracija"


def main() -> None:
    conn = psycopg.connect(ADMIN_DSN)
    conn.autocommit = True

    try:
        conn.execute(f"CREATE DATABASE {TARGET_DB};")
        print(f"OK: database '{TARGET_DB}' was created")
    except psycopg.errors.DuplicateDatabase:
        print(f"OK: database '{TARGET_DB}' already exists")
    except psycopg.errors.InsufficientPrivilege:
        print(
            "ERROR: current role cannot create databases.\n"
            "Run scripts/postgres_bootstrap.sql as a PostgreSQL superuser,\n"
            "then retry starting the app."
        )
    finally:
        conn.close()


if __name__ == "__main__":
    main()
