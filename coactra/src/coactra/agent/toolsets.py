"""Toolset construction helpers for Agent runtimes.

Keeps optional MCP and auth dependencies out of the runtime constructor until a
gateway or additive mcp() tag is actually used.
"""
from __future__ import annotations

from typing import Any


def _token_auth(auth: Any) -> Any:
    from coactra.agent.auth import BearerAuth, StaticToken  # noqa: PLC0415

    if isinstance(auth, str):
        auth = StaticToken(auth)
    return BearerAuth(auth) if auth is not None else None


def build_mcp_toolsets(
    *,
    gateway: str | None = None,
    auth: Any = None,
    mcp_servers: list[Any] | None = None,
) -> tuple[Any | None, list[Any]]:
    """Build the primary gateway toolset plus additive mcp() toolsets.

    Returns ``(gateway_toolset, additive_toolsets)`` so callers can preserve the
    public debug attributes without knowing pydantic-ai construction details.
    """
    if gateway is None and not mcp_servers:
        return None, []

    from pydantic_ai.mcp import MCPToolset  # noqa: PLC0415

    gateway_toolset = None
    if gateway is not None:
        gateway_auth = _token_auth(auth)
        gateway_toolset = (
            MCPToolset(gateway, auth=gateway_auth)
            if gateway_auth is not None
            else MCPToolset(gateway)
        )

    additive: list[Any] = []
    for server in mcp_servers or []:
        kwargs: dict[str, Any] = {}
        server_name = getattr(server, "name", None)
        if server_name is not None:
            kwargs["id"] = server_name
        server_auth = _token_auth(getattr(server, "auth", None))
        if server_auth is not None:
            kwargs["auth"] = server_auth
        additive.append(MCPToolset(getattr(server, "url"), **kwargs))

    return gateway_toolset, additive
