"""Telegram webhook endpoint."""

from __future__ import annotations

from typing import Any

from aiogram.types import Update
from fastapi import APIRouter, Depends, Response, status

from ...logger_factory import get_logger
from ...services.telegram_bot import TelegramBotRunner
from ..dependencies import get_telegram_bot

logger = get_logger(__name__)

router = APIRouter(prefix="/telegram", tags=["telegram"])


@router.post("/webhook")
async def telegram_webhook(
    update_data: dict[str, Any],
    telegram_bot: TelegramBotRunner = Depends(get_telegram_bot),
) -> Response:
    """Handle incoming webhook updates from Telegram."""
    logger.info(
        "Webhook received: update_id=%s, has_message=%s",
        update_data.get("update_id"),
        "message" in update_data,
    )

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
