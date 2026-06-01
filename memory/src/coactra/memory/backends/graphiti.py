"""GraphitiBackend — wraps ``graphiti_core.Graphiti`` (natively async).

graphiti builds a temporal knowledge graph from episodes and recalls relationship
"facts". This adapter maps ``Scope`` onto graphiti's ``group_id`` namespace via the fixed
3-slot ``Scope.key`` (``tenant:agent_or_*:session_or_*`` — tenant always first, so
isolation holds; injective, so distinct scopes never collide), calls the native async
API, and maps graphiti's ``EntityEdge`` objects into plain ``Recollection``s. No
graphiti type ever crosses the boundary.

Note the API asymmetry (verified against graphiti_core): ``add_episode`` takes
``group_id`` (singular str); ``search`` takes ``group_ids`` (list) and ``num_results``.

``graphiti_core`` imports lazily — only ``MissingExtraError`` is raised when a backend
is constructed without the extra.
"""

from __future__ import annotations

from collections.abc import Sequence
from datetime import datetime, timezone
from typing import Any

from coactra.memory.backends._errors import MissingExtraError
from coactra.memory.backends.base import event_text
from coactra.memory.capabilities import Capability
from coactra.memory.export import ExportReport
from coactra.memory.types import MemoryEvent, Recollection, Scope

_SOURCE = "graphiti"
_CAPS = {
    Capability.STORE,
    Capability.GRAPH_EDGES,
    Capability.TEMPORAL,
    Capability.PROVENANCE,
}


def _group_id(scope: Scope) -> str:
    """Map Scope → a graphiti-LEGAL, injective group_id.

    graphiti validates ``group_id`` against ``[A-Za-z0-9_-]`` only. The canonical
    ``Scope.key`` uses ':' separators and '*' placeholders — both ILLEGAL there. We
    hex-encode the key: the result is legal AND injective (distinct scopes → distinct
    ids), so tenant isolation is preserved. ``Scope`` still forbids ':' / '*' / empty
    in its fields, keeping ``key`` collision-resistant before encoding.
    """
    return "fl" + scope.key.encode("utf-8").hex()


def _edge_to_recollection(edge: Any, score: float) -> Recollection:
    """Map a graphiti EntityEdge → Recollection. Reads only documented attributes."""
    when = getattr(edge, "valid_at", None)
    return Recollection(
        text=str(getattr(edge, "fact", "")),
        score=score,
        source_id=str(getattr(edge, "uuid", "")),
        when=when if isinstance(when, datetime) else None,
        metadata={
            "source_backend": _SOURCE,
            "group_id": getattr(edge, "group_id", None),
        },
    )


class GraphitiBackend:
    """Adapter over ``graphiti_core.Graphiti``. Inject a client for tests; build one otherwise."""

    declared_capabilities = set(_CAPS)

    def __init__(
        self,
        *,
        client: Any | None = None,
        uri: str | None = None,
        user: str | None = None,
        password: str | None = None,
    ) -> None:
        if client is not None:
            self._client = client
            return
        try:
            from graphiti_core import Graphiti  # noqa: PLC0415  (lazy: optional extra)
        except ImportError as exc:  # pragma: no cover - exercised only without the extra
            raise MissingExtraError("graphiti") from exc
        self._client = Graphiti(uri, user, password)

    async def capabilities(self) -> set[Capability]:
        return set(_CAPS)

    async def remember(self, events: Sequence[MemoryEvent], scope: Scope) -> None:
        gid = _group_id(scope)
        now = datetime.now(timezone.utc)
        for i, event in enumerate(events):
            text = event_text(event)
            if not text:
                continue
            await self._client.add_episode(
                name=f"{gid}:{now.timestamp()}:{i}",
                episode_body=text,
                source_description="coactra.memory",
                reference_time=now,
                group_id=gid,
            )

    async def recall(self, query: str, scope: Scope, k: int = 10) -> list[Recollection]:
        edges = await self._client.search(
            query=query,
            group_ids=[_group_id(scope)],
            num_results=k,
        )
        # graphiti returns a relevance-ranked list with no per-edge score; synthesize a
        # descending positional score so ordering is preserved through the boundary.
        n = len(edges)
        return [
            _edge_to_recollection(edge, score=(n - i) / n if n else 0.0)
            for i, edge in enumerate(edges)
        ]

    async def dump(self, scope: Scope) -> list[Recollection]:
        # graphiti has no scope-wide "dump everything"; the broad-recall path is the
        # closest honest approximation for export. Empty query → engine default search.
        edges = await self._client.search(query="", group_ids=[_group_id(scope)])
        return [_edge_to_recollection(edge, score=0.0) for edge in edges]

    async def ingest(self, items: Sequence[Recollection], scope: Scope) -> ExportReport:
        gid = _group_id(scope)
        now = datetime.now(timezone.utc)
        written = 0
        for i, item in enumerate(items):
            if not item.text:
                continue
            await self._client.add_episode(
                name=f"{gid}:ingest:{now.timestamp()}:{i}",
                episode_body=item.text,
                source_description="coactra.memory:export",
                reference_time=now,
                group_id=gid,
            )
            written += 1
        return ExportReport(
            transferred=written,
            source_backend="",
            target_backend=type(self).__name__,
        )
