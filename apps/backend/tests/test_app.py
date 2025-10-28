"""Basic sanity tests for the backend application bootstrap."""

from backend.application import BotApp, bootstrap


def test_bootstrap_creates_bot_app(monkeypatch, tmp_path) -> None:
    """Ensure the bootstrap function produces a configured application instance."""
    monkeypatch.setenv("APP_ENV", "test")
    monkeypatch.setenv("BOT_LOG_LEVEL", "DEBUG")
    monkeypatch.setenv("OPENAI_API_KEY", "test-key")
    monkeypatch.setenv("TELEGRAM_BOT_TOKEN", "123456:TEST")
    monkeypatch.setenv("DATABASE_URL", f"sqlite+aiosqlite:///{tmp_path/'bootstrap.db'}")

    app = bootstrap()

    assert isinstance(app, BotApp)
    assert app.config.environment == "test"
    assert app.config.log_level == "DEBUG"
    assert app.config.openai_model == "gpt-4.1-mini"
