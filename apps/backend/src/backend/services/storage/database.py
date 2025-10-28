"""Async SQLAlchemy engine and session management."""

from __future__ import annotations

from contextlib import asynccontextmanager
from typing import AsyncIterator

from sqlalchemy.ext.asyncio import AsyncEngine, AsyncSession, async_sessionmaker, create_async_engine

from .models import Base


class Database:
    """Wrap async SQLAlchemy engine configuration for the bot runtime."""

    def __init__(self, url: str) -> None:
        self._engine: AsyncEngine = create_async_engine(url, future=True)
        self._session_factory: async_sessionmaker[AsyncSession] = async_sessionmaker(
            bind=self._engine,
            expire_on_commit=False,
        )

    async def initialize(self) -> None:
        """Create database tables if they do not already exist."""
        async with self._engine.begin() as connection:
            await connection.run_sync(Base.metadata.create_all)

    @asynccontextmanager
    async def session(self) -> AsyncIterator[AsyncSession]:
        """Provide an async session context."""
        async with self._session_factory() as session:
            yield session

    async def dispose(self) -> None:
        """Close the underlying engine."""
        await self._engine.dispose()

