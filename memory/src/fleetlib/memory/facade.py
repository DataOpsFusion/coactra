"""Memory — the clean, wrappable public facade.

Async-first: ``remember``/``recall``/``export`` are coroutines over an injected
``MemoryBackend``. ``Memory.sync`` is a thin blocking bridge exposing the same three
methods for synchronous callers and quick scripts. The facade holds NO storage logic of
its own — it delegates to the backend and keeps the surface tiny so a2a / the
openai-sdk / the agent lib can wrap it in a few lines.
"""

from __future__ import annotations

import asyncio
from collections.abc import Sequence

from fleetlib.memory.backends.base import MemoryBackend
from fleetlib.memory.export import ExportReport, export as _export
from fleetlib.memory.types import MemoryEvent, Recollection, Scope


def _ensure_no_running_loop() -> None:
    """Fail fast (and clearly) if a sync-bridge call is made from within an event loop."""
    try:
        asyncio.get_running_loop()
    except RuntimeError:
        return  # no loop running → safe to drive one
    raise RuntimeError(
        "Memory.sync.* cannot be called from a running event loop; "
        "await the async Memory methods instead."
    )


class _SyncBridge:
    """Blocking mirror of the async facade. Each call drives the coroutine to completion.

    Uses ``asyncio.run`` per call — intended for synchronous callers. Calling these from
    inside a running event loop raises a clear error (use the async methods there).
    """

    def __init__(self, mem: "Memory") -> None:
        self._mem = mem

    def remember(self, events: Sequence[MemoryEvent], scope: Scope) -> None:
        _ensure_no_running_loop()
        return asyncio.run(self._mem.remember(events, scope))

    def recall(self, query: str, scope: Scope, k: int = 10) -> list[Recollection]:
        _ensure_no_running_loop()
        return asyncio.run(self._mem.recall(query, scope, k))

    def export(self, *, to: MemoryBackend, scope: Scope) -> ExportReport:
        _ensure_no_running_loop()
        return asyncio.run(self._mem.export(to=to, scope=scope))


class Memory:
    """Async memory facade wrapping an injected backend."""

    def __init__(self, *, backend: MemoryBackend) -> None:
        self._backend = backend
        self.sync = _SyncBridge(self)

    @property
    def backend(self) -> MemoryBackend:
        return self._backend

    async def remember(self, events: Sequence[MemoryEvent], scope: Scope) -> None:
        """Hand conversational events to the backend; the engine extracts/consolidates."""
        await self._backend.remember(events, scope)

    async def recall(self, query: str, scope: Scope, k: int = 10) -> list[Recollection]:
        """Recall the top-k recollections for ``query`` within ``scope``."""
        return await self._backend.recall(query, scope, k)

    async def export(self, *, to: MemoryBackend, scope: Scope) -> ExportReport:
        """Move this memory's scope into another backend (lossy; off the headline)."""
        return await _export(self._backend, to, scope=scope)
