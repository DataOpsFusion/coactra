"""OAuth 2.1 client-credentials token source with auto-refresh.

This module provides a lightweight ``TokenSource`` abstraction — fetch and
cache a bearer token; nothing more. It is intentionally separate from the
RFC 8693 token-*exchange* flow in ``coactra.agent.identity``.

The ``[oauth]`` extra (``httpx``) is **not** required at import time.
``httpx`` is imported lazily inside ``oidc()`` so plain ``import coactra``
stays light.
"""
from __future__ import annotations

import time
from collections.abc import Callable
from typing import Any, Protocol, runtime_checkable

__all__ = ["TokenSource", "StaticToken", "oidc"]


# ---------------------------------------------------------------------------
# Protocol
# ---------------------------------------------------------------------------

@runtime_checkable
class TokenSource(Protocol):
    """Anything that can hand back a currently-valid bearer token."""

    async def token(self) -> str:
        """Return a currently-valid bearer token."""
        ...


# ---------------------------------------------------------------------------
# StaticToken — trivial implementation for dev / testing
# ---------------------------------------------------------------------------

class StaticToken:
    """A ``TokenSource`` that always returns the same fixed value."""

    def __init__(self, value: str) -> None:
        self._value = value

    async def token(self) -> str:
        return self._value


# ---------------------------------------------------------------------------
# oidc() — client-credentials fetch + cache + auto-refresh
# ---------------------------------------------------------------------------

class _OidcTokenSource:
    """Internal implementation returned by ``oidc()``."""

    def __init__(
        self,
        token_url: str,
        client_id: str,
        client_secret: str,
        *,
        scope: str | None,
        http: Any,  # async callable: (token_url, form) -> dict
        leeway: float,
        clock: Callable[[], float],
    ) -> None:
        self._token_url = token_url
        self._client_id = client_id
        self._client_secret = client_secret
        self._scope = scope
        self._http = http
        self._leeway = leeway
        self._clock = clock

        # Cache state
        self._cached_token: str | None = None
        self._expiry: float = 0.0  # monotonic time at which token expires (minus leeway)

    async def token(self) -> str:
        now = self._clock()
        if self._cached_token is not None and now < self._expiry:
            return self._cached_token

        # Fetch a fresh token
        form: dict[str, str] = {
            "grant_type": "client_credentials",
            "client_id": self._client_id,
            "client_secret": self._client_secret,
        }
        if self._scope is not None:
            form["scope"] = self._scope

        http = self._http
        if http is None:
            # Lazy default: build a one-shot httpx.AsyncClient call
            import httpx  # noqa: PLC0415

            async def _default_http(token_url: str, frm: dict) -> dict:
                async with httpx.AsyncClient() as client:
                    resp = await client.post(token_url, data=frm)
                    resp.raise_for_status()
                    return resp.json()

            http = _default_http

        response: dict[str, Any] = await http(self._token_url, form)
        access_token: str = response["access_token"]
        expires_in: float = float(response.get("expires_in", 3600))

        # Store with leeway applied
        self._cached_token = access_token
        self._expiry = self._clock() + expires_in - self._leeway
        return access_token


def oidc(
    token_url: str,
    client_id: str,
    client_secret: str,
    *,
    scope: str | None = None,
    http: Any = None,
    leeway: float = 30.0,
    clock: Callable[[], float] = time.monotonic,
) -> TokenSource:
    """Return a ``TokenSource`` that fetches OAuth 2.1 client-credentials tokens.

    Parameters
    ----------
    token_url:
        The token endpoint URL (e.g. ``https://auth.example.com/realms/myrealm/token``).
    client_id:
        The OAuth client identifier.
    client_secret:
        The OAuth client secret.
    scope:
        Optional space-separated OAuth scopes to request.
    http:
        Injectable async callable ``async (token_url: str, form: dict) -> dict``.
        Defaults to a lazily-constructed ``httpx.AsyncClient`` POST.
        Provide a fake for tests.
    leeway:
        Seconds before actual expiry to treat the token as expired and refetch.
        Default: 30 seconds.
    clock:
        Monotonic clock callable returning ``float`` seconds. Injectable for tests.
        Default: ``time.monotonic``.
    """
    return _OidcTokenSource(
        token_url=token_url,
        client_id=client_id,
        client_secret=client_secret,
        scope=scope,
        http=http,
        leeway=leeway,
        clock=clock,
    )
