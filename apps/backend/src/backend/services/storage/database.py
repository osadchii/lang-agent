"""Async SQLAlchemy engine and session management."""

from __future__ import annotations

from contextlib import asynccontextmanager
from typing import AsyncIterator

from sqlalchemy.ext.asyncio import AsyncEngine, AsyncSession, async_sessionmaker, create_async_engine

from .migrations import upgrade_head


class Database:
    """Wrap async SQLAlchemy engine configuration for the bot runtime."""

    def __init__(self, url: str) -> None:
        self._database_url = url
        self._engine: AsyncEngine = create_async_engine(url, future=True)
        self._session_factory: async_sessionmaker[AsyncSession] = async_sessionmaker(
            bind=self._engine,
            expire_on_commit=False,
        )

    async def initialize(self) -> None:
        """Ensure the database schema is migrated to the latest revision."""
        await upgrade_head(self._database_url)

    @asynccontextmanager
    async def session(self) -> AsyncIterator[AsyncSession]:
        """Provide an async session context."""
        async with self._session_factory() as session:
            yield session

    async def dispose(self) -> None:
        """Close the underlying engine."""
        await self._engine.dispose()
