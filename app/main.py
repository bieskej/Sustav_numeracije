from __future__ import annotations

from pathlib import Path

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from dotenv import load_dotenv

from app.core.config import load_settings
from app.core.database import Database, init_db
from app.api import (
    assignments,
    deps,
    lokacije,
    msisdn,
    opcine,
    operatori,
    postal_codes,
    rasponi,
    reports,
    statistike,
    uredjaji,
)


FRONTEND_DIR = Path(__file__).resolve().parents[1] / "frontend"


def create_app() -> FastAPI:
    load_dotenv()
    settings = load_settings()

    db = Database(settings.database_url)
    init_db(db)

    app = FastAPI(title="MSISDN Numeracija API (RS)", version="2.0.0")

    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_allow_origins,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    app.dependency_overrides[deps.get_database] = lambda: db

    app.include_router(opcine.router)
    app.include_router(lokacije.router)
    app.include_router(uredjaji.router)
    app.include_router(operatori.router)
    app.include_router(rasponi.router)
    app.include_router(msisdn.router)
    app.include_router(postal_codes.router)
    app.include_router(assignments.router)
    app.include_router(reports.router)
    app.include_router(statistike.router)

    if FRONTEND_DIR.exists():
        app.mount("/frontend", StaticFiles(directory=str(FRONTEND_DIR), html=True), name="frontend")

        @app.get("/", include_in_schema=False)
        def frontend_index() -> FileResponse:
            return FileResponse(FRONTEND_DIR / "index.html")

    return app


app = create_app()

