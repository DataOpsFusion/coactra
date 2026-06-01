"""InProcessBackend — the ONE working default adapter.

Pydantic-only, no embeddings, no external service. Tenant-isolated dict keyed by
Scope.key. learn() stores typed items with trivial content-dedup (it does NOT run a
consolidation algorithm — smarter consolidation arrives by swapping in a real engine).
recall() is lexical token-overlap. This is the opinionated default that works out of
the box; advanced users swap the backend.
"""

from __future__ import annotations

from collections.abc import Iterable, Sequence

from fleetlib.memory.backend import normalize_events
from fleetlib.memory.capabilities import Capability
from fleetlib.memory.models import MemoryEvent, MemoryItem
from fleetlib.memory.scope import Scope

_SOURCE = "inprocess"


class InProcessBackend:
    """In-memory, tenant-isolated memory store."""

    def __init__(self) -> None:
        self._store: dict[str, list[MemoryItem]] = {}

    def capabilities(self) -> set[Capability]:
        return {Capability.STORE, Capability.LEXICAL_RECALL, Capability.PROVENANCE}

    def _bucket(self, scope: Scope) -> list[MemoryItem]:
        return self._store.setdefault(scope.key, [])

    def learn(self, events: Iterable[str | MemoryEvent], scope: Scope) -> list[MemoryItem]:
        bucket = self._bucket(scope)
        existing = {i.content for i in bucket}
        learned: list[MemoryItem] = []
        for event in normalize_events(events):
            if event.content in existing:
                continue
            item = MemoryItem.from_event(event, source_backend=_SOURCE)
            bucket.append(item)
            existing.add(event.content)
            learned.append(item)
        return learned

    def dump(self, scope: Scope) -> list[MemoryItem]:
        return list(self._bucket(scope))

    def ingest(self, items: Sequence[MemoryItem], scope: Scope) -> list[MemoryItem]:
        bucket = self._bucket(scope)
        existing = {i.content for i in bucket}
        added: list[MemoryItem] = []
        for item in items:
            if item.content in existing:
                continue
            bucket.append(item)
            existing.add(item.content)
            added.append(item)
        return added

    @staticmethod
    def _tokens(text: str) -> set[str]:
        return {t for t in "".join(c if c.isalnum() else " " for c in text.lower()).split() if t}

    def recall(
        self,
        query: str,
        scope: Scope,
        capabilities: set[Capability] | None = None,
        limit: int = 10,
    ) -> list[MemoryItem]:
        if capabilities:
            unsupported = capabilities - self.capabilities()
            if unsupported:
                names = ", ".join(sorted(c.name for c in unsupported))
                raise ValueError(
                    f"InProcessBackend cannot shape recall to capabilities: {names}"
                )
        q = self._tokens(query)
        scored: list[tuple[int, MemoryItem]] = []
        for item in self._bucket(scope):
            overlap = len(q & self._tokens(item.content))
            if overlap:
                scored.append((overlap, item))
        scored.sort(key=lambda pair: pair[0], reverse=True)
        return [item for _, item in scored[:limit]]
