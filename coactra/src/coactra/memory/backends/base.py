"""MemoryBackend — the async, swappable SPI.

Every method takes a Scope; tenant isolation is part of the contract, not the caller's
job. The headline pair is ``remember``/``recall``. ``dump``/``ingest`` are the export
seam (read a scope's items out, write items into a target). ``capabilities`` powers
lossy export negotiation. The default ``InProcessBackend`` is the one fully-offline
implementation; ``Mem0Backend``/``GraphitiBackend`` wrap real engines.
"""

from __future__ import annotations

from collections.abc import Iterable, Sequence
from typing import TYPE_CHECKING, Protocol, runtime_checkable

from coactra.memory.capabilities import Capability
from coactra.memory.types import MemoryEvent, Recollection, Scope

if TYPE_CHECKING:  # avoid a runtime import cycle (export imports base)
    from coactra.memory.export import ExportReport


def event_text(event: MemoryEvent) -> str:
    """Flatten a MemoryEvent (str or chat-message dict) to plain text."""
    if isinstance(event, str):
        return event
    return str(event.get("content", "")).strip()


def normalize_events(events: Iterable[MemoryEvent]) -> list[MemoryEvent]:
    """Pass events through untouched as a concrete list (engines may iterate twice)."""
    return list(events)


@runtime_checkable
class MemoryBackend(Protocol):
    """The contract every backend satisfies. Async-first."""

    async def remember(self, events: Sequence[MemoryEvent], scope: Scope) -> None:
        """Hand conversational events to the engine; it extracts/consolidates."""
        ...

    async def recall(self, query: str, scope: Scope, k: int = 10) -> list[Recollection]:
        """Retrieve the top-k recollections for ``query`` within ``scope``."""
        ...

    async def capabilities(self) -> set[Capability]:
        """Declare the Capability subset this backend supports."""
        ...

    async def dump(self, scope: Scope) -> list[Recollection]:
        """Read all recollections in scope (export source side)."""
        ...

    async def ingest(self, items: Sequence[Recollection], scope: Scope) -> ExportReport:
        """Write recollections into scope (export target side); report the result."""
        ...
