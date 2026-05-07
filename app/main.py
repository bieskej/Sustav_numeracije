from __future__ import annotations

from contextlib import asynccontextmanager
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
    health,
    import_csv,
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
from app.services.karantena_cleanup import run_karantena_cleanup


FRONTEND_DIR = Path(__file__).resolve().parents[1] / "frontend"


def create_app() -> FastAPI:
    load_dotenv()
    settings = load_settings()

    db = Database(settings.database_url)
    init_db(db)

    @asynccontextmanager
    async def lifespan(app: FastAPI):
        try:
            from apscheduler.schedulers.background import BackgroundScheduler
            scheduler = BackgroundScheduler()
            scheduler.add_job(
                lambda: run_karantena_cleanup(db),
                "cron",
                hour=0,
                minute=0,
                id="karantena_cleanup",
                replace_existing=True,
            )
            scheduler.start()
        except Exception:
            scheduler = None  # type: ignore[assignment]

        yield

        if scheduler is not None:
            scheduler.shutdown(wait=False)

    app = FastAPI(
        title="MSISDN Numeracija API (HT Eronet)",
        version="2.1.0",
        lifespan=lifespan,
    )

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
    app.include_router(health.router)
    app.include_router(import_csv.router)

    if FRONTEND_DIR.exists():
        app.mount("/frontend", StaticFiles(directory=str(FRONTEND_DIR), html=True), name="frontend")

        @app.get("/", include_in_schema=False)
        def frontend_index() -> FileResponse:
            return FileResponse(
                FRONTEND_DIR / "index.html",
                headers={"Cache-Control": "no-cache, no-store, must-revalidate"},
            )

    return app


app = create_app()
