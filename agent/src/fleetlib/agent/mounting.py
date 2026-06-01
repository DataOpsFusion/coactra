"""Mid-session MCP capability mounting — the first session-level gap.

MCP already supports live tool changes (tools.listChanged, FastMCP live mounting, OpenAI
Agents SDK re-lists per run + invalidate_tools_cache). What's missing is the SESSION
ORCHESTRATION: mount a server mid-session but expose its tools only on the NEXT SAFE MODEL
TURN, resolve naming conflicts, and invalidate the tool cache. This module owns exactly
that — it does NOT re-implement MCP.

The turn boundary (the charter's open question) is DEFINED here, observably: stage() puts
a mount into `pending`; begin_turn() promotes pending->active and fires on_invalidate.
A staged mount is therefore never visible during the current turn — only the next one.
"""

from __future__ import annotations

from collections.abc import Callable
from typing import Protocol, runtime_checkable

from fleetlib.agent.scope import Scope
from fleetlib.agent.tools import ToolSpec


class MountConflictError(RuntimeError):
    """Raised by a ConflictPolicy that refuses to resolve a tool-name collision."""


@runtime_checkable
class MCPServerPort(Protocol):
    def list_tools(self) -> list[str]:
        """Return the bare tool names this server exposes."""
        ...


@runtime_checkable
class ConflictPolicy(Protocol):
    def resolve(self, incoming: ToolSpec, active: list[ToolSpec]) -> ToolSpec:
        """Return the ToolSpec to add (possibly renamed), or raise MountConflictError."""
        ...


class NamespaceByMountId:
    """Default ConflictPolicy — never collides: the mount id namespaces the tool name.

    ToolSpec.qualified_name already carries `${mount_id}.${name}`, so two mounts exposing
    the same bare name stay distinct. This policy is a no-op pass-through that documents
    the rule and leaves a hook for stricter policies (e.g. reject) to be swapped in.
    """

    def resolve(self, incoming: ToolSpec, active: list[ToolSpec]) -> ToolSpec:
        return incoming


class MountRegistry:
    """Holds the active toolset and a pending set staged for the next safe turn."""

    def __init__(
        self,
        scope: Scope,
        *,
        conflict_policy: ConflictPolicy | None = None,
        on_invalidate: Callable[[], None] | None = None,
    ) -> None:
        self.scope = scope
        self.conflict_policy: ConflictPolicy = conflict_policy or NamespaceByMountId()
        self._on_invalidate = on_invalidate
        self._active: list[ToolSpec] = []
        self._pending: list[tuple[str, MCPServerPort]] = []

    def stage(self, mount_id: str, server: MCPServerPort) -> None:
        """Stage a mount. Its tools become visible only after the next begin_turn()."""
        self._pending.append((mount_id, server))

    def begin_turn(self) -> None:
        """Promote every pending mount into the active toolset (the safe-turn boundary)."""
        if not self._pending:
            return
        for mount_id, server in self._pending:
            for name in server.list_tools():
                spec = ToolSpec(name=name, mount_id=mount_id)
                resolved = self.conflict_policy.resolve(spec, self._active)
                self._active.append(resolved)
        self._pending.clear()
        if self._on_invalidate is not None:
            self._on_invalidate()

    def active_tools(self) -> list[ToolSpec]:
        """The toolset the model sees THIS turn (excludes anything staged this turn)."""
        return list(self._active)
