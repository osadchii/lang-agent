"""Helpers for running Alembic migrations from application code."""

from __future__ import annotations

import asyncio
from pathlib import Path

from alembic import command
from alembic.config import Config

_ROOT_DIR = Path(__file__).resolve().parents[4]


def _build_config(database_url: str) -> Config:
    """Construct an Alembic config bound to the provided database URL."""
    config_path = _ROOT_DIR / "alembic.ini"
    script_location = _ROOT_DIR / "migrations"
    config = Config(str(config_path))
    config.set_main_option("sqlalchemy.url", database_url)
    config.set_main_option("script_location", str(script_location))
    config.set_main_option("prepend_sys_path", str(_ROOT_DIR / "src"))
    config.attributes["configure_logger"] = False
    return config


async def upgrade_head(database_url: str) -> None:
    """Upgrade the database schema to the latest revision."""
    config = _build_config(database_url)
    loop = asyncio.get_running_loop()
    await loop.run_in_executor(None, command.upgrade, config, "head")
