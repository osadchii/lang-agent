"""Basic sanity tests for the bot application bootstrap."""

from bot.app import BotApp, bootstrap


def test_bootstrap_creates_bot_app(monkeypatch) -> None:
    """Ensure the bootstrap function produces a configured application instance."""
    monkeypatch.setenv("APP_ENV", "test")
    monkeypatch.setenv("BOT_LOG_LEVEL", "DEBUG")
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)

    app = bootstrap()

    assert isinstance(app, BotApp)
    assert app.config.environment == "test"
    assert app.config.log_level == "DEBUG"
