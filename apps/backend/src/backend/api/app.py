"""Factory for constructing the HTTP API application."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Awaitable, Callable


@dataclass
class PlaceholderAPI:
    """Minimal ASGI-compatible placeholder until the real framework is wired."""

    async def __call__(self, scope: dict[str, Any], receive: Callable[..., Awaitable[Any]], send: Callable[..., Awaitable[Any]]) -> None:
        """Respond with 501 while the HTTP API surface is under construction."""
        raise NotImplementedError("API layer not yet implemented")


def create_api() -> PlaceholderAPI:
    """Produce the API application instance to be mounted by an ASGI server."""
    return PlaceholderAPI()
