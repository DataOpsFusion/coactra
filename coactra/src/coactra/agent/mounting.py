"""Mid-session MCP capability mounting — the first session-level gap.

MCP already supports live tool changes (tools.listChanged, FastMCP live mounting, OpenAI
Agents SDK re-list + invalidate cache). What's missing is the SESSION ORCHESTRATION: mount
a server mid-session but expose its tools only on the NEXT SAFE MODEL TURN, resolve naming
conflicts deterministically, and invalidate the tool cache. This module owns exactly that;
it does NOT re-implement MCP.

Two real DSA mechanisms live here:

1.  A **prefix trie** (`_ToolTrie`) keyed on the dotted qualified name (`<mount>.<tool>`).
    Insert/lookup are O(number of path segments), prefix enumeration (`under("fs")`) walks
    one subtree, and a name collision is detected precisely at a TERMINAL node — that is
    where the deterministic `ConflictPolicy` decides (namespace by default, or reject).
2.  A per-registry **state machine**: a mount is `pending` until an observable
    `begin_turn()` boundary promotes it to `active` and fires cache invalidation. A staged
    mount is therefore NEVER visible during the current turn — only the next one.
"""

from __future__ import annotations

from collections.abc import Callable, Iterator
from typing import Protocol, runtime_checkable

from coactra.agent.domain import Scope, ToolSpec


class MountConflictError(RuntimeError):
    """Raised by a ConflictPolicy that refuses to resolve a tool-name collision."""


@runtime_checkable
class MCPServerPort(Protocol):
    def list_tools(self) -> list[str]:
        """Return the bare tool names this server exposes."""
        ...


@runtime_checkable
class ConflictPolicy(Protocol):
    def resolve(self, incoming: ToolSpec, existing: ToolSpec) -> ToolSpec:
        """Resolve a collision at one terminal trie node.

        Called only when `incoming.qualified_name == existing.qualified_name`. Return the
        ToolSpec to keep (possibly a renamed one), or raise MountConflictError to refuse.
        """
        ...


class NamespaceByMountId:
    """Default ConflictPolicy.

    The qualified name already namespaces by mount id (`<mount>.<tool>`), so two DIFFERENT
    mounts never collide. A collision can only happen if the SAME mount id is staged twice
    with the same tool — last-writer-wins (idempotent re-mount), which this policy permits
    by keeping the incoming spec.
    """

    def resolve(self, incoming: ToolSpec, existing: ToolSpec) -> ToolSpec:
        return incoming


class RejectOnConflict:
    """Strict ConflictPolicy — refuses ANY terminal collision instead of resolving it."""

    def resolve(self, incoming: ToolSpec, existing: ToolSpec) -> ToolSpec:
        raise MountConflictError(incoming.qualified_name)


class _TrieNode:
    """One node of the tool-name prefix trie. Children are keyed by name segment; a
    non-None `spec` marks a terminal (a real tool lives at this dotted path)."""

    __slots__ = ("children", "spec")

    def __init__(self) -> None:
        self.children: dict[str, _TrieNode] = {}
        self.spec: ToolSpec | None = None


class ToolTrie:
    """A prefix trie over dotted qualified tool names (`<mount>.<tool>`).

    - insert / lookup are O(#segments), independent of the toolset size;
    - `under(prefix)` enumerates a whole subtree (all tools of a mount) by walking down to
      the prefix node once, then collecting its terminals;
    - a collision is detected exactly at a terminal node and handed to the ConflictPolicy.
    """

    def __init__(self, conflict_policy: ConflictPolicy | None = None) -> None:
        self._root = _TrieNode()
        self._policy: ConflictPolicy = conflict_policy or NamespaceByMountId()
        self._count = 0

    @staticmethod
    def _segments(qualified: str) -> list[str]:
        return qualified.split(".")

    def insert(self, spec: ToolSpec) -> None:
        """Insert a tool at its qualified path. A terminal collision goes to the policy."""
        node = self._root
        for seg in self._segments(spec.qualified_name):
            node = node.children.setdefault(seg, _TrieNode())
        if node.spec is not None:
            # Terminal collision — the deterministic decision point.
            node.spec = self._policy.resolve(spec, node.spec)
        else:
            node.spec = spec
            self._count += 1

    def lookup(self, qualified: str) -> ToolSpec | None:
        """O(#segments) exact lookup of a tool by its qualified name."""
        node = self._root
        for seg in self._segments(qualified):
            node = node.children.get(seg)
            if node is None:
                return None
        return node.spec

    def under(self, prefix: str) -> list[ToolSpec]:
        """Every tool whose qualified name starts with `<prefix>.` — one subtree walk.

        `prefix` is a mount id (or any leading segment path). Walking to the prefix node is
        O(#prefix segments); collecting its terminals is O(size of that subtree).
        """
        node = self._root
        for seg in self._segments(prefix):
            node = node.children.get(seg)
            if node is None:
                return []
        return list(self._collect(node))

    def _collect(self, node: _TrieNode) -> Iterator[ToolSpec]:
        if node.spec is not None:
            yield node.spec
        for child in node.children.values():
            yield from self._collect(child)

    def all_specs(self) -> list[ToolSpec]:
        return list(self._collect(self._root))

    def __len__(self) -> int:
        return self._count


class MountRegistry:
    """The mount state machine: `pending` mounts staged this turn, promoted to `active`
    (into the trie) only at the next `begin_turn()` boundary, with cache invalidation."""

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
        self._trie = ToolTrie(conflict_policy=self.conflict_policy)
        self._pending: list[tuple[str, MCPServerPort]] = []

    def stage(self, mount_id: str, server: MCPServerPort) -> None:
        """Stage a mount (state: pending). Visible only after the next begin_turn()."""
        self._pending.append((mount_id, server))

    def begin_turn(self) -> None:
        """Promote every pending mount into the active trie (the safe-turn boundary).

        ATOMIC, all-or-nothing semantics. Promotion builds a NEW trie seeded from the
        currently-active specs plus every pending insert, and swaps it in only on full
        success. If a ConflictPolicy rejects a pending mount (e.g. RejectOnConflict),
        the raise propagates UNCHANGED, but the live trie is left untouched and `_pending`
        is already drained — so a rejected mount can never leak a partial promotion nor
        permanently wedge future begin_turn cycles. `on_invalidate` fires only after a
        successful swap.
        """
        if not self._pending:
            return
        pending, self._pending = self._pending, []
        rebuilt = ToolTrie(conflict_policy=self.conflict_policy)
        for spec in self._trie.all_specs():
            rebuilt.insert(spec)
        for mount_id, server in pending:
            for name in server.list_tools():
                rebuilt.insert(ToolSpec(name=name, mount_id=mount_id))
        # Swap in only after the full batch validated — a mid-batch raise above never
        # reaches here, leaving the live trie consistent.
        self._trie = rebuilt
        if self._on_invalidate is not None:
            self._on_invalidate()

    def active_tools(self) -> list[ToolSpec]:
        """The toolset the model sees THIS turn (excludes anything staged this turn)."""
        return self._trie.all_specs()

    def tools_under(self, mount_id: str) -> list[ToolSpec]:
        """Active tools contributed by one mount — an O(prefix) trie subtree walk."""
        return self._trie.under(mount_id)

    def lookup(self, qualified_name: str) -> ToolSpec | None:
        """Resolve an active tool by its qualified name (O(#segments))."""
        return self._trie.lookup(qualified_name)
