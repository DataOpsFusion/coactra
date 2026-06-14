"""ToolSpec — the unit the MountRegistry tracks and the agent's toolset exposes.

Carries its mount-id provenance so conflict resolution can namespace a tool by the mount
it came from (qualified_name). This is data only; the actual tool invocation belongs to
the MCP transport, which the agent layer never re-implements.
"""

from __future__ import annotations

from pydantic import BaseModel, Field


class ToolSpec(BaseModel):
    """A tool exposed by a mounted MCP server, tagged with the mount it came from."""

    model_config = {"frozen": True}

    name: str = Field(min_length=1)
    mount_id: str = Field(min_length=1)

    @property
    def qualified_name(self) -> str:
        """The collision-free name: the mount id namespaces the bare tool name."""
        return f"{self.mount_id}.{self.name}"


class MCPServer(BaseModel):
    """An additive remote MCP server requested through the public mcp() helper."""

    model_config = {"frozen": True}

    url: str = Field(min_length=1)
    name: str | None = None
    auth: object | None = None


def mcp(url: str, *, name: str | None = None, auth: object | None = None) -> MCPServer:
    """Tag a remote MCP server so Team-built agents can expand it as a toolset."""
    return MCPServer(url=url, name=name, auth=auth)
