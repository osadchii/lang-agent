"""Telegram webhook endpoint."""

from __future__ import annotations

import logging
from typing import Any

from aiogram.types import Update
from fastapi import APIRouter, Depends, Response, status

from ...services.telegram_bot import TelegramBotRunner
from ..dependencies import get_telegram_bot

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/telegram", tags=["telegram"])


@router.post("/webhook")
async def telegram_webhook(
    update_data: dict[str, Any],
    telegram_bot: TelegramBotRunner = Depends(get_telegram_bot),
) -> Response:
    """Handle incoming webhook updates from Telegram."""
    # Force logging through root logger to debug configuration issues
    import sys
    print(f"[WEBHOOK DEBUG] Webhook called!", file=sys.stderr, flush=True)

    try:
        # Log through multiple loggers to test which one works
        print(f"[WEBHOOK DEBUG] About to log to root logger", file=sys.stderr, flush=True)
        root_logger = logging.getLogger()
        root_logger.info("[ROOT] Webhook received: update_id=%s", update_data.get("update_id"))
        print(f"[WEBHOOK DEBUG] Root logger done", file=sys.stderr, flush=True)

        logger.info(
            "Webhook received: update_id=%s, has_message=%s",
            update_data.get("update_id"),
            "message" in update_data,
        )
        print(f"[WEBHOOK DEBUG] Child logger done", file=sys.stderr, flush=True)

        # Also log logger configuration for debugging
        logger.info(
            "Logger config: name=%s, level=%s, propagate=%s, handlers=%s, parent=%s",
            logger.name,
            logging.getLevelName(logger.level),
            logger.propagate,
            [type(h).__name__ for h in logger.handlers],
            logger.parent.name if logger.parent else None,
        )
        print(f"[WEBHOOK DEBUG] All logging complete", file=sys.stderr, flush=True)
    except Exception as e:
        print(f"[WEBHOOK DEBUG] ERROR during logging: {e}", file=sys.stderr, flush=True)
        import traceback
        traceback.print_exc()

    try:
        # Parse the update from the incoming JSON
        update = Update(**update_data)

        logger.info(
            "Processing update: update_id=%s, type=%s",
            update.update_id,
            "message" if update.message else "callback" if update.callback_query else "other",
        )

        # Process the update through the dispatcher
        await telegram_bot.process_update(update)

        logger.info("Update processed successfully: update_id=%s", update.update_id)

        return Response(status_code=status.HTTP_200_OK)
    except Exception:
        logger.exception(
            "Failed to process Telegram update: update_id=%s",
            update_data.get("update_id"),
        )
        # Return 200 anyway to prevent Telegram from retrying
        return Response(status_code=status.HTTP_200_OK)
