"""
Telegram Mini App authentication validation.

Validates initData received from Telegram WebApp to ensure requests
are genuinely coming from authenticated Telegram users.

Reference: https://core.telegram.org/bots/webapps#validating-data-received-via-the-mini-app
"""

import hashlib
import hmac
from dataclasses import dataclass
from typing import Optional
from urllib.parse import parse_qsl


@dataclass(frozen=True)
class TelegramUser:
    """Validated Telegram user data from initData."""

    id: int
    first_name: str
    last_name: Optional[str] = None
    username: Optional[str] = None
    language_code: Optional[str] = None
    is_premium: Optional[bool] = None
    photo_url: Optional[str] = None


class TelegramAuthError(Exception):
    """Raised when Telegram initData validation fails."""

    pass


def validate_init_data(init_data: str, bot_token: str) -> dict[str, str]:
    """
    Validate Telegram WebApp initData and return parsed parameters.

    Args:
        init_data: The raw initData string from window.Telegram.WebApp.initData
        bot_token: Your Telegram bot token

    Returns:
        Dictionary of validated parameters

    Raises:
        TelegramAuthError: If validation fails or hash doesn't match

    Example:
        >>> init_data = "query_id=...&user=%7B%22id%22%3A123...&hash=abc123..."
        >>> params = validate_init_data(init_data, "YOUR_BOT_TOKEN")
        >>> print(params['user'])  # JSON string with user data
    """
    if not init_data:
        raise TelegramAuthError("initData is empty")

    # Parse query string into key-value pairs
    params = dict(parse_qsl(init_data))

    # Extract hash sent by Telegram
    received_hash = params.pop("hash", None)
    if not received_hash:
        raise TelegramAuthError("Missing hash in initData")

    # Create data_check_string: sorted key=value pairs joined by newlines
    data_check_string = "\n".join(f"{key}={value}" for key, value in sorted(params.items()))

    # Compute secret key: HMAC-SHA256(bot_token, "WebAppData")
    secret_key = hmac.new(
        key="WebAppData".encode(),
        msg=bot_token.encode(),
        digestmod=hashlib.sha256,
    ).digest()

    # Compute expected hash: HMAC-SHA256(secret_key, data_check_string)
    expected_hash = hmac.new(
        key=secret_key,
        msg=data_check_string.encode(),
        digestmod=hashlib.sha256,
    ).hexdigest()

    # Validate hash matches
    if not hmac.compare_digest(expected_hash, received_hash):
        raise TelegramAuthError("Invalid hash: initData may have been tampered with")

    return params


def parse_telegram_user(init_data: str, bot_token: str) -> TelegramUser:
    """
    Validate initData and extract Telegram user information.

    Args:
        init_data: The raw initData string from Telegram WebApp
        bot_token: Your Telegram bot token

    Returns:
        TelegramUser with validated user data

    Raises:
        TelegramAuthError: If validation fails or user data is missing

    Example:
        >>> user = parse_telegram_user(init_data, bot_token)
        >>> print(f"Authenticated user: {user.id}")
    """
    import json

    params = validate_init_data(init_data, bot_token)

    user_json = params.get("user")
    if not user_json:
        raise TelegramAuthError("Missing user data in initData")

    try:
        user_data = json.loads(user_json)
    except json.JSONDecodeError as exc:
        raise TelegramAuthError("Invalid user JSON in initData") from exc

    # Validate required fields
    if "id" not in user_data or "first_name" not in user_data:
        raise TelegramAuthError("User data missing required fields (id, first_name)")

    return TelegramUser(
        id=user_data["id"],
        first_name=user_data["first_name"],
        last_name=user_data.get("last_name"),
        username=user_data.get("username"),
        language_code=user_data.get("language_code"),
        is_premium=user_data.get("is_premium"),
        photo_url=user_data.get("photo_url"),
    )
