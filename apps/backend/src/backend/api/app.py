"""Factory for constructing the HTTP API application."""

from __future__ import annotations

from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from .dependencies import build_container, set_container
from .routers import decks, training


def create_api() -> FastAPI:
    """Produce the FastAPI application instance to be mounted by an ASGI server."""
    container = build_container()
    set_container(container)

    @asynccontextmanager
    async def lifespan(_: FastAPI):
        await container.database.initialize()
        try:
            yield
        finally:
            await container.database.dispose()

    app = FastAPI(
        title="Lang Agent API",
        version="0.1.0",
        lifespan=lifespan,
    )

    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_credentials=False,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    @app.get("/health", tags=["system"])
    async def healthcheck() -> dict[str, str]:
        """Simple readiness probe."""
        return {"status": "ok"}

    app.include_router(decks.router, prefix="/api")
    app.include_router(training.router, prefix="/api")
    return app
