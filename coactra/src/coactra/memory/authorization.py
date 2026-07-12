"""Optional scoped-memory authorization wrapper.

Memory engines remain unaware of organization models. Hosts bind this narrow port to
their preferred policy system and opt into enforcement by wrapping a ``Memory`` facade.
"""

from __future__ import annotations

from collections.abc import Sequence
from enum import StrEnum

from coactra.memory.facade import Memory
from coactra.memory.types import MemoryEvent, Recollection
from coactra.policy import Policy, PolicyRequest
from coactra.scope import Scope


class MemoryAccess(StrEnum):
    read = "read"
    write = "write"


class MemoryAccessDenied(PermissionError):
    """Raised when an actor attempts to use a memory scope without a grant."""


class AuthorizedMemory:
    """Enforce read/write policy before delegating to a ``Memory`` facade."""

    def __init__(
        self,
        memory: Memory,
        *,
        actor: str,
        policy: Policy,
    ) -> None:
        self._memory = memory
        self._actor = actor
        self._policy = policy

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
        request = PolicyRequest(
            principal=self._actor,
            action=f"memory.{access.value}",
            resource=f"memory:{scope.key}",
            scope=scope,
            component="memory",
            context={"memory_access": access.value, "memory_scope": scope.key},
        )
        decision = await self._policy.check(request)
        if not decision.allowed:
            reason = decision.reason or (
                f"{self._actor!r} is not allowed to {access.value} memory scope {scope.key!r}"
            )
            raise MemoryAccessDenied(reason)
