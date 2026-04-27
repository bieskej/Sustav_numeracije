from __future__ import annotations

from collections.abc import Generator

from fastapi import Depends
from psycopg import Connection

from app.core.database import Database, get_db


def get_database() -> Database:
    # Overridden at app startup with dependency_overrides
    raise RuntimeError("Database dependency not overridden")


def db_dep(db: Database = Depends(get_database)) -> Generator[Connection, None, None]:
    yield from get_db(db)

