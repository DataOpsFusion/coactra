"""Memory protocols — small async contracts for pluggable memory.

Every method takes a Scope; tenant isolation is part of the contract, not the caller's
job. ``recall`` is the minimum contract. ``remember`` and export/import are optional
seams for engines that support them.
"""

from __future__ import annotations

import inspect
from collections.abc import Awaitable, Callable, Iterable, Sequence
from typing import TYPE_CHECKING, Any, Protocol, runtime_checkable

from coactra.memory.capabilities import Capability
from coactra.memory.types import MemoryEvent, Recollection
from coactra.scope import Scope

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


RecallRows = Sequence[Recollection | str]
RecallCallable = Callable[..., Awaitable[RecallRows] | RecallRows]


@runtime_checkable
class MemoryReader(Protocol):
    async def recall(self, query: str, scope: Scope, k: int = 10) -> list[Recollection]:
        """Retrieve the top-k recollections for ``query`` within ``scope``."""
        ...


@runtime_checkable
class MemoryWriter(Protocol):
    async def remember(self, events: Sequence[MemoryEvent], scope: Scope) -> None:
        """Hand conversational events to the engine; it extracts/consolidates."""
        ...


@runtime_checkable
class MemoryExporter(Protocol):
    async def capabilities(self) -> set[Capability]:
        """Declare the Capability subset this backend supports."""
        ...

    async def dump(self, scope: Scope) -> list[Recollection]:
        """Read all recollections in scope (export source side)."""
        ...

    async def ingest(self, items: Sequence[Recollection], scope: Scope) -> ExportReport:
        """Write recollections into scope (export target side); report the result."""
        ...


def _as_recollection(item: Recollection | str) -> Recollection:
    if isinstance(item, Recollection):
        return item
    return Recollection(text=str(item))


async def _maybe_await(value: Any) -> Any:
    if inspect.isawaitable(value):
        return await value
    return value


class CallableMemoryReader:
    """Adapter for simple recall callables."""

    def __init__(self, recall: RecallCallable) -> None:
        self._recall = recall

    async def recall(self, query: str, scope: Scope, k: int = 10) -> list[Recollection]:
        try:
            raw = self._recall(query=query, scope=scope, k=k)
        except TypeError:
            raw = self._recall(query)
        rows = await _maybe_await(raw)
        return [_as_recollection(row) for row in list(rows)[:k]]
