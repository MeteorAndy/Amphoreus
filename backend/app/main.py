from __future__ import annotations

from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api import router as api_router
from app.core.api_keys import _ensure_config
from app.core.config import settings


@asynccontextmanager
async def _lifespan(_app: FastAPI) -> AsyncIterator[None]:
    """Ensure config skeleton exists before the first request arrives."""
    _ensure_config(settings.THE_WORLD_DATA_DIR)
    yield


def create_app() -> FastAPI:
    """Build and return a fully configured FastAPI application instance."""
    app = FastAPI(
        title="The World — Novel & Screenplay Engine",
        version="0.1.0",
        description=(
            "An AI-powered novel and screenplay generation engine backed by "
            "DeepSeek and OpenViking."
        ),
        lifespan=_lifespan,
        docs_url="/docs" if settings.DEBUG else None,
        redoc_url="/redoc" if settings.DEBUG else None,
    )

    # -- middleware -----------------------------------------------------------
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # -- routers --------------------------------------------------------------
    app.include_router(api_router)

    # -- routes ---------------------------------------------------------------
    @app.get("/health")
    async def health_check():
        """Lightweight liveness probe."""
        return {"status": "ok", "version": "0.1.0"}

    return app


# Module-level convenience instance for ``uvicorn`` CLI.
app = create_app()
