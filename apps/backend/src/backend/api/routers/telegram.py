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
    try:
        # Parse the update from the incoming JSON
        update = Update(**update_data)

        # Process the update through the dispatcher
        await telegram_bot.process_update(update)

        return Response(status_code=status.HTTP_200_OK)
    except Exception:
        logger.exception("Failed to process Telegram update")
        # Return 200 anyway to prevent Telegram from retrying
        return Response(status_code=status.HTTP_200_OK)
