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


def test_bootstrap_composes_database_url_from_parts(monkeypatch) -> None:
    """The configuration should derive database URL from granular settings when not provided."""
    for key in ("DATABASE_URL", "DB_DRIVER", "DB_HOST", "DB_PORT", "DB_NAME", "DB_USER", "DB_PASSWORD"):
        monkeypatch.delenv(key, raising=False)

    monkeypatch.setenv("APP_ENV", "test")
    monkeypatch.setenv("BOT_LOG_LEVEL", "INFO")
    monkeypatch.setenv("OPENAI_API_KEY", "test-key")
    monkeypatch.setenv("TELEGRAM_BOT_TOKEN", "123456:TEST")

    monkeypatch.setenv("DB_DRIVER", "postgresql+asyncpg")
    monkeypatch.setenv("DB_HOST", "db.internal")
    monkeypatch.setenv("DB_PORT", "6500")
    monkeypatch.setenv("DB_NAME", "lang_agent_test")
    monkeypatch.setenv("DB_USER", "bot_user")
    monkeypatch.setenv("DB_PASSWORD", "Sup#r Secret")

    app = bootstrap()

    assert app.config.database_url == "postgresql+asyncpg://bot_user:Sup%23r+Secret@db.internal:6500/lang_agent_test"
