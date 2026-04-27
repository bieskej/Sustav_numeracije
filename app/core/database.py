from __future__ import annotations

from collections.abc import Generator
from dataclasses import dataclass
from pathlib import Path

import psycopg
from psycopg import Connection
from psycopg.rows import dict_row


@dataclass(frozen=True)
class Database:
    dsn: str

    def connect(self) -> Connection:
        conn = psycopg.connect(self.dsn, row_factory=dict_row)
        conn.execute("SET TIME ZONE 'UTC'")
        return conn


MIGRATIONS_DIR = Path(__file__).resolve().parents[2] / "migrations"


def get_db(db: Database) -> Generator[Connection, None, None]:
    conn = db.connect()
    try:
        yield conn
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()


def init_db(db: Database) -> None:
    MIGRATIONS_DIR.mkdir(parents=True, exist_ok=True)

    migration_files = sorted(p for p in MIGRATIONS_DIR.glob("*.sql") if p.is_file())
    with db.connect() as conn:
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS schema_migrations (
              version TEXT PRIMARY KEY,
              applied_at TIMESTAMPTZ NOT NULL DEFAULT now()
            )
            """
        )

        applied = {
            r["version"]
            for r in conn.execute("SELECT version FROM schema_migrations").fetchall()
        }

        for path in migration_files:
            version = path.name
            if version in applied:
                continue
            sql = path.read_text(encoding="utf-8")
            with conn.transaction():
                conn.execute(sql)
                conn.execute(
                    "INSERT INTO schema_migrations (version) VALUES (%s)", (version,)
                )

