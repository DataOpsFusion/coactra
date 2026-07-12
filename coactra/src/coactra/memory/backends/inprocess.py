"""InProcessBackend — the default, fully-offline backend.

Pydantic-only, no embeddings, no external service, no engine reimplemented. A
tenant-isolated dict keyed by ``Scope.key`` holds ``Recollection`` records.
``remember`` flattens events to text and stores them with trivial content-dedup (it
does NOT run real consolidation — that arrives by swapping in mem0/graphiti).
``recall`` is lexical token-overlap. This is the opinionated default that works out of
the box; advanced users inject another backend.

Async only to satisfy the SPI — the work is synchronous and instant, so the methods
simply ``return`` without awaiting anything.
"""

from __future__ import annotations

import uuid
from collections.abc import Sequence
from datetime import UTC, datetime

from coactra.memory.backends.base import event_text, normalize_events
from coactra.memory.capabilities import Capability
from coactra.memory.export import ExportReport
from coactra.memory.types import MemoryEvent, Recollection
from coactra.scope import Scope

_SOURCE = "inprocess"
_CAPS = {Capability.STORE, Capability.LEXICAL_RECALL, Capability.PROVENANCE}


def _tokens(text: str) -> set[str]:
    return {t for t in "".join(c if c.isalnum() else " " for c in text.lower()).split() if t}


class InProcessBackend:
    """In-memory, tenant-isolated memory store."""

    def __init__(self) -> None:
        self._store: dict[str, list[Recollection]] = {}

    async def capabilities(self) -> set[Capability]:
        return set(_CAPS)

    def _bucket(self, scope: Scope) -> list[Recollection]:
        return self._store.setdefault(scope.key, [])

    async def remember(self, events: Sequence[MemoryEvent], scope: Scope) -> None:
        bucket = self._bucket(scope)
        existing = {r.text for r in bucket}
        for event in normalize_events(events):
            text = event_text(event)
            if not text or text in existing:
                continue
            bucket.append(
                Recollection(
                    text=text,
                    source_id=uuid.uuid4().hex,
                    when=datetime.now(UTC),
                    metadata={"source_backend": _SOURCE},
                )
            )
            existing.add(text)

    async def recall(self, query: str, scope: Scope, k: int = 10) -> list[Recollection]:
        q = _tokens(query)
        scored: list[tuple[int, Recollection]] = []
        for rec in self._bucket(scope):
            overlap = len(q & _tokens(rec.text))
            if overlap:
                scored.append((overlap, rec))
        scored.sort(key=lambda pair: pair[0], reverse=True)
        out: list[Recollection] = []
        for overlap, rec in scored[:k]:
            out.append(rec.model_copy(update={"score": float(overlap)}))
        return out

    async def dump(self, scope: Scope) -> list[Recollection]:
        # score is meaningless without a query → 0.0 (see Recollection docstring).
        return [r.model_copy(update={"score": 0.0}) for r in self._bucket(scope)]

    async def ingest(self, items: Sequence[Recollection], scope: Scope) -> ExportReport:
        bucket = self._bucket(scope)
        existing = {r.text for r in bucket}
        written = 0
        for item in items:
            if item.text in existing:
                continue
            bucket.append(item.model_copy(deep=True))
            existing.add(item.text)
            written += 1
        return ExportReport.from_ingest(self, transferred=written)
