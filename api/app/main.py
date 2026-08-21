"""FastAPI application entrypoint."""

from __future__ import annotations

import asyncio
import logging
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.config import get_settings
from app.pipeline import register_default_stages
from app.routes import clips as clips_routes
from app.routes import jobs as jobs_routes
from app.routes import ws as ws_routes

logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(_app: FastAPI):
    settings = get_settings()
    settings.jobs_dir.mkdir(parents=True, exist_ok=True)
    settings.cache_dir.mkdir(parents=True, exist_ok=True)
    settings.whisper_model_dir.mkdir(parents=True, exist_ok=True)
    register_default_stages()
    logger.info("Clipper API ready (storage=%s)", settings.storage_dir)
    yield
    # No background workers to shut down in M2.


def create_app() -> FastAPI:
    settings = get_settings()
    app = FastAPI(
        title="Clipper API",
        version="0.1.0",
        lifespan=lifespan,
    )
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origins,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )
    app.include_router(jobs_routes.router, prefix="/api")
    app.include_router(clips_routes.router, prefix="/api")
    app.include_router(ws_routes.router, prefix="/api")

    @app.get("/api/health")
    async def health() -> dict[str, str]:
        return {"status": "ok"}

    return app


app = create_app()


def run() -> None:
    """Console-script entrypoint: `clipper-api`."""
    settings = get_settings()
    import uvicorn

    uvicorn.run(
        "app.main:app",
        host=settings.api_host,
        port=settings.api_port,
        reload=False,
    )


if __name__ == "__main__":
    run()
