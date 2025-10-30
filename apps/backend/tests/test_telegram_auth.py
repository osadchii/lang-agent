"""Tests for Telegram WebApp authentication validation."""

from __future__ import annotations

import hashlib
import hmac
from urllib.parse import urlencode

import pytest

from backend.services.telegram_auth import (
    TelegramAuthError,
    TelegramUser,
    parse_telegram_user,
    validate_init_data,
)


def create_valid_init_data(bot_token: str, **params) -> str:
    """
    Generate a valid Telegram initData string with correct HMAC signature.

    Args:
        bot_token: Bot token to sign with
        **params: Parameters to include in initData (e.g., user='{"id":123}')

    Returns:
        URL-encoded initData string with valid hash
    """
    # Create data_check_string: sorted params joined by newlines
    data_check_string = "\n".join(f"{key}={value}" for key, value in sorted(params.items()))

    # Compute secret key
    secret_key = hmac.new(
        key="WebAppData".encode(),
        msg=bot_token.encode(),
        digestmod=hashlib.sha256,
    ).digest()

    # Compute hash
    computed_hash = hmac.new(
        key=secret_key,
        msg=data_check_string.encode(),
        digestmod=hashlib.sha256,
    ).hexdigest()

    # Add hash to params
    all_params = {**params, "hash": computed_hash}
    return urlencode(all_params)


def test_validate_init_data_with_valid_signature():
    """Valid initData should pass validation."""
    bot_token = "123456:ABC-DEF1234ghIkl-zyx57W2v1u123ew11"
    init_data = create_valid_init_data(
        bot_token,
        query_id="AAHdF6IQAAAAAN0XohDhrOrc",
        user='{"id":123,"first_name":"Test"}',
        auth_date="1234567890",
    )

    params = validate_init_data(init_data, bot_token)

    assert params["query_id"] == "AAHdF6IQAAAAAN0XohDhrOrc"
    assert params["user"] == '{"id":123,"first_name":"Test"}'
    assert params["auth_date"] == "1234567890"
    assert "hash" not in params  # Hash is removed after validation


def test_validate_init_data_rejects_tampered_data():
    """Modified initData should fail validation."""
    bot_token = "123456:ABC-DEF1234ghIkl-zyx57W2v1u123ew11"
    init_data = create_valid_init_data(
        bot_token,
        user='{"id":123,"first_name":"Test"}',
    )

    # Tamper with the data (change user ID)
    tampered = init_data.replace("123", "999")

    with pytest.raises(TelegramAuthError, match="Invalid hash"):
        validate_init_data(tampered, bot_token)


def test_validate_init_data_rejects_missing_hash():
    """initData without hash should fail."""
    init_data = urlencode({"user": '{"id":123}', "auth_date": "1234567890"})

    with pytest.raises(TelegramAuthError, match="Missing hash"):
        validate_init_data(init_data, "fake_token")


def test_validate_init_data_rejects_empty_string():
    """Empty initData should fail."""
    with pytest.raises(TelegramAuthError, match="initData is empty"):
        validate_init_data("", "fake_token")


def test_parse_telegram_user_extracts_user_data():
    """Valid user data should be parsed correctly."""
    bot_token = "123456:ABC-DEF1234ghIkl-zyx57W2v1u123ew11"
    user_json = '{"id":99887766,"first_name":"Ivan","last_name":"Petrov","username":"ivan_p","language_code":"ru","is_premium":true}'

    init_data = create_valid_init_data(
        bot_token,
        user=user_json,
        auth_date="1234567890",
    )

    user = parse_telegram_user(init_data, bot_token)

    assert isinstance(user, TelegramUser)
    assert user.id == 99887766
    assert user.first_name == "Ivan"
    assert user.last_name == "Petrov"
    assert user.username == "ivan_p"
    assert user.language_code == "ru"
    assert user.is_premium is True


def test_parse_telegram_user_handles_minimal_data():
    """User with only required fields should work."""
    bot_token = "123456:ABC-DEF1234ghIkl-zyx57W2v1u123ew11"
    user_json = '{"id":123,"first_name":"John"}'

    init_data = create_valid_init_data(bot_token, user=user_json)

    user = parse_telegram_user(init_data, bot_token)

    assert user.id == 123
    assert user.first_name == "John"
    assert user.last_name is None
    assert user.username is None


def test_parse_telegram_user_rejects_missing_user_field():
    """initData without user field should fail."""
    bot_token = "123456:ABC-DEF1234ghIkl-zyx57W2v1u123ew11"
    init_data = create_valid_init_data(bot_token, query_id="test123")

    with pytest.raises(TelegramAuthError, match="Missing user data"):
        parse_telegram_user(init_data, bot_token)


def test_parse_telegram_user_rejects_invalid_json():
    """Malformed user JSON should fail."""
    bot_token = "123456:ABC-DEF1234ghIkl-zyx57W2v1u123ew11"
    init_data = create_valid_init_data(bot_token, user="not-valid-json")

    with pytest.raises(TelegramAuthError, match="Invalid user JSON"):
        parse_telegram_user(init_data, bot_token)


def test_parse_telegram_user_rejects_missing_required_fields():
    """User JSON without id or first_name should fail."""
    bot_token = "123456:ABC-DEF1234ghIkl-zyx57W2v1u123ew11"

    # Missing id
    init_data1 = create_valid_init_data(bot_token, user='{"first_name":"John"}')
    with pytest.raises(TelegramAuthError, match="missing required fields"):
        parse_telegram_user(init_data1, bot_token)

    # Missing first_name
    init_data2 = create_valid_init_data(bot_token, user='{"id":123}')
    with pytest.raises(TelegramAuthError, match="missing required fields"):
        parse_telegram_user(init_data2, bot_token)


def test_validate_init_data_with_special_characters():
    """InitData with URL-encoded special characters should work."""
    bot_token = "123456:ABC-DEF1234ghIkl-zyx57W2v1u123ew11"
    user_json = '{"id":123,"first_name":"Иван","last_name":"Петров"}'

    init_data = create_valid_init_data(bot_token, user=user_json)

    user = parse_telegram_user(init_data, bot_token)

    assert user.first_name == "Иван"
    assert user.last_name == "Петров"
