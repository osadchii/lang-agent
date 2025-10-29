"""Tests for database schema initialization via Alembic migrations."""

from __future__ import annotations

import pytest
from sqlalchemy import text

from backend.services.storage.database import Database


@pytest.mark.asyncio
async def test_initialize_runs_migrations(tmp_path) -> None:
    """Database.initialize should apply Alembic migrations."""
    db_path = tmp_path / "migrations.db"
    database = Database(f"sqlite+aiosqlite:///{db_path}")

    await database.initialize()

    async with database.session() as session:
        result = await session.execute(
            text("SELECT name FROM sqlite_master WHERE type='table' AND name='users'")
        )
        assert result.scalar_one_or_none() == "users"

        columns = await session.execute(text("PRAGMA table_info('messages')"))
        column_names = [row[1] for row in columns]
        assert {"user_id", "direction", "content"} <= set(column_names)

    await database.dispose()
