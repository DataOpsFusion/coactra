"""FastMCP adapter — STUB. Will satisfy MCPServerPort; raises until the mcp extra."""

from __future__ import annotations

from coactra.agent.adapters._stub import require_extra


class FastMCPServer:
    satisfies = "MCPServerPort"

    def __init__(self, *args, **kwargs) -> None:
        require_extra("mcp")
