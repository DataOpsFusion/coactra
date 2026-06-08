"""OAuth bearer token helpers for MCP gateway auth.

This module provides a lightweight ``TokenSource`` abstraction. For OAuth
client-credentials token fetch and refresh, use ``authlib`` or ``httpx-oauth``.

``httpx`` is **not** required at import time for plain ``import coactra``:
this module is itself lazily loaded. ``BearerAuth`` subclasses ``httpx.Auth``
and is available once the ``[agent]`` or ``[oauth]`` extra is installed.
"""

from __future__ import annotations

from collections.abc import AsyncGenerator
from typing import Any, Protocol, runtime_checkable

try:  # Optional: only gateway/oauth users need httpx at runtime.
    import httpx as _httpx
except ImportError:  # pragma: no cover - exercised in base-install subprocess tests.
    _httpx = None

_AuthBase = _httpx.Auth if _httpx is not None else object

__all__ = ["TokenSource", "StaticToken", "BearerAuth"]


@runtime_checkable
class TokenSource(Protocol):
    """Anything that can hand back a currently-valid bearer token."""

    async def token(self) -> str:
        """Return a currently-valid bearer token."""
        ...


class BearerAuth(_AuthBase):  # type: ignore[misc,valid-type]
    """An ``httpx.Auth`` subclass that injects a bearer token per request."""

    def __init__(self, source: TokenSource) -> None:
        self._source = source

    async def async_auth_flow(self, request: Any) -> AsyncGenerator[Any, Any]:
        token = await self._source.token()
        request.headers["Authorization"] = f"Bearer {token}"
        yield request


class StaticToken:
    """A ``TokenSource`` that always returns the same fixed value."""

    def __init__(self, value: str) -> None:
        self._value = value

    async def token(self) -> str:
        return self._value
