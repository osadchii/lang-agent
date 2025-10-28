"""HTTP API surface for integrations such as the Telegram mini app."""

from .app import create_api

__all__ = ["create_api"]
