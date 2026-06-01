"""MemoryBackend — the swappable SPI.

Every method takes a Scope; isolation is part of the contract, not the caller's job.
dump()/ingest() are the export seam: dump() reads a scope's items out, ingest() writes
(possibly degraded) items into a target. The default InProcessBackend is the ONE working
implementation; mem0/graphiti/letta are optional-extra stubs.
"""

from __future__ import annotations

from collections.abc import Iterable, Sequence
from typing import Protocol, runtime_checkable

from fleetlib.memory.capabilities import Capability
from fleetlib.memory.models import MemoryEvent, MemoryItem
from fleetlib.memory.scope import Scope


def normalize_events(events: Iterable[str | MemoryEvent]) -> list[MemoryEvent]:
    """Accept plain strings or MemoryEvents; return MemoryEvents."""
    out: list[MemoryEvent] = []
    for e in events:
        out.append(e if isinstance(e, MemoryEvent) else MemoryEvent(content=e))
    return out


@runtime_checkable
class MemoryBackend(Protocol):
    def capabilities(self) -> set[Capability]:
        """Declare the Capability subset this backend supports."""
        ...

    def learn(self, events: Iterable[str | MemoryEvent], scope: Scope) -> list[MemoryItem]:
        """Consolidate conversational events into stored items within scope."""
        ...

    def recall(
        self,
        query: str,
        scope: Scope,
        capabilities: set[Capability] | None = None,
        limit: int = 10,
    ) -> list[MemoryItem]:
        """Retrieve items for query within scope, shaped to caller capabilities."""
        ...

    def dump(self, scope: Scope) -> list[MemoryItem]:
        """Read all items in scope (export source side)."""
        ...

    def ingest(self, items: Sequence[MemoryItem], scope: Scope) -> list[MemoryItem]:
        """Write items into scope (export target side)."""
        ...
