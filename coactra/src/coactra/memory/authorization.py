"""Optional scoped-memory authorization wrapper.

Memory engines remain unaware of organization models. Hosts bind this narrow port to
their preferred policy system and opt into enforcement by wrapping a ``Memory`` facade.
"""

from __future__ import annotations

from collections.abc import Iterable, Sequence
from enum import StrEnum
from typing import Protocol, runtime_checkable

from coactra.memory.facade import Memory
from coactra.memory.types import MemoryEvent, Recollection, Scope


class MemoryAccess(StrEnum):
    read = "read"
    write = "write"


@runtime_checkable
class MemoryAuthorizer(Protocol):
    async def allowed(self, actor: str, access: MemoryAccess, scope: Scope) -> bool:
        """Return whether ``actor`` may access the exact memory scope."""
        ...


class AllowListMemoryAuthorizer:
    """Default-deny exact-scope policy for local use and deterministic tests."""

    def __init__(
        self,
        grants: Iterable[tuple[str, MemoryAccess, Scope]] = (),
    ) -> None:
        self._grants = {(actor, access, scope.key) for actor, access, scope in grants}

    def grant(self, actor: str, access: MemoryAccess, scope: Scope) -> None:
        self._grants.add((actor, access, scope.key))

    def revoke(self, actor: str, access: MemoryAccess, scope: Scope) -> None:
        self._grants.discard((actor, access, scope.key))

    async def allowed(self, actor: str, access: MemoryAccess, scope: Scope) -> bool:
        return (actor, access, scope.key) in self._grants


class MemoryAccessDenied(PermissionError):
    """Raised when an actor attempts to use a memory scope without a grant."""


class AuthorizedMemory:
    """Enforce read/write policy before delegating to a ``Memory`` facade."""

    def __init__(
        self,
        memory: Memory,
        *,
        actor: str,
        authorizer: MemoryAuthorizer,
    ) -> None:
        self._memory = memory
        self._actor = actor
        self._authorizer = authorizer

    @property
    def backend(self):
        return self._memory.backend

    async def remember(self, events: Sequence[MemoryEvent], scope: Scope) -> None:
        await self._require(MemoryAccess.write, scope)
        await self._memory.remember(events, scope)

    async def recall(self, query: str, scope: Scope, k: int = 10) -> list[Recollection]:
        await self._require(MemoryAccess.read, scope)
        return await self._memory.recall(query, scope, k)

    async def _require(self, access: MemoryAccess, scope: Scope) -> None:
        if not await self._authorizer.allowed(self._actor, access, scope):
            raise MemoryAccessDenied(
                f"{self._actor!r} is not allowed to {access.value} memory scope {scope.key!r}"
            )
