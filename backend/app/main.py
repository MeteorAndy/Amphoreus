from __future__ import annotations

from contextlib import asynccontextmanager
from typing import AsyncIterator

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.characters import router as char_router
from app.api.guardian import router as guardian_router
from app.api.pipeline import router as pipeline_router
from app.api.plot import router as plot_router
from app.api.scene import router as scene_router
from app.api.world import router as world_router
from app.api.writer import router as writer_router
from app.core.config import get_settings


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    """Startup / shutdown lifecycle for OpenViking and Kuzu."""
    settings = get_settings()
    settings.data_dir.mkdir(parents=True, exist_ok=True)

    # Future: init OpenViking, Kuzu here
    yield


def create_app() -> FastAPI:
    settings = get_settings()

    app = FastAPI(
        title="Amphoreus Story Engine",
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

    @app.get("/health")
    async def health() -> dict[str, str]:
        return {"status": "ok"}

    app.include_router(world_router)
    app.include_router(char_router)
    app.include_router(plot_router)
    app.include_router(guardian_router)
    app.include_router(scene_router)
    app.include_router(writer_router)
    app.include_router(pipeline_router)

    return app


def main() -> None:
    import uvicorn

    settings = get_settings()
    uvicorn.run(
        "app.main:create_app",
        host=settings.host,
        port=settings.port,
        reload=settings.debug,
        log_level=settings.log_level.lower(),
        factory=True,
    )


if __name__ == "__main__":
    main()
