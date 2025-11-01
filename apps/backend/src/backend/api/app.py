"""Factory for constructing the HTTP API application."""

from __future__ import annotations

import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from ..logging import configure_logging
from .dependencies import build_container, set_container
from .routers import decks, training, telegram

logger = logging.getLogger(__name__)


def create_api() -> FastAPI:
    """Produce the FastAPI application instance to be mounted by an ASGI server."""
    container = build_container()
    set_container(container)

    # Configure logging with Loki support
    configure_logging(
        level=container.config.log_level,
        loki_url=container.config.loki_url,
        loki_labels=container.config.loki_labels,
    )

    @asynccontextmanager
    async def lifespan(_: FastAPI):
        await container.database.initialize()

        # Set up Telegram webhook if URL is configured
        if container.config.telegram_webhook_url:
            try:
                await container.telegram_bot.set_webhook(container.config.telegram_webhook_url)
            except Exception:
                logger.exception("Failed to set Telegram webhook")

        try:
            yield
        finally:
            # Clean up webhook on shutdown
            if container.config.telegram_webhook_url:
                try:
                    await container.telegram_bot.delete_webhook()
                except Exception:
                    logger.exception("Failed to delete Telegram webhook")

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
    app.include_router(telegram.router, prefix="/api")
    return app
