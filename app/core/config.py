from __future__ import annotations

from dataclasses import dataclass
import os


@dataclass(frozen=True)
class Settings:
    database_url: str
    cors_allow_origins: list[str]


def load_settings() -> Settings:
    database_url = os.getenv("DATABASE_URL", "").strip()
    if not database_url:
        raise RuntimeError(
            "DATABASE_URL is required (e.g. postgresql://user:pass@host:5432/dbname)"
        )

    cors_raw = os.getenv("CORS_ALLOW_ORIGINS", "*").strip()
    cors_allow_origins = ["*"] if cors_raw == "*" else [o.strip() for o in cors_raw.split(",") if o.strip()]

    return Settings(database_url=database_url, cors_allow_origins=cors_allow_origins)

