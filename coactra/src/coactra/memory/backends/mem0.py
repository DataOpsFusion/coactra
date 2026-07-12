"""Mem0Backend — wraps mem0's sync ``Memory`` behind the async SPI.

mem0 already does extraction + consolidation + vector recall. This adapter is a thin
connector: it maps ``Scope`` onto mem0's ``user_id``/``agent_id``/``run_id`` scoping,
calls the sync engine, and maps mem0's result dicts into plain ``Recollection`` objects.
No mem0 type ever crosses the boundary.

``mem0`` imports lazily: the module imports fine without the extra, and only
``MissingExtraError`` is raised when a backend is actually constructed without it.
"""

from __future__ import annotations

from collections.abc import Sequence
from datetime import datetime
from typing import Any

from coactra.memory.backends._errors import MissingExtraError
from coactra.memory.backends.base import event_text
from coactra.memory.capabilities import Capability
from coactra.memory.export import ExportReport
from coactra.memory.types import MemoryEvent, Recollection
from coactra.scope import Scope

_SOURCE = "mem0"
_CAPS = {Capability.STORE, Capability.VECTOR_EMBEDDING, Capability.PROVENANCE}


def _scope_kwargs(scope: Scope) -> dict[str, str]:
    """Map the complete canonical scope to mem0's filtering fields."""
    kwargs: dict[str, str] = {"user_id": f"{scope.tenant_id}:{scope.namespace}"}
    if scope.agent_id is not None:
        kwargs["agent_id"] = scope.agent_id
    if scope.session_id is not None:
        kwargs["run_id"] = scope.session_id
    return kwargs


def _parse_when(value: Any) -> datetime | None:
    if isinstance(value, str) and value:
        try:
            return datetime.fromisoformat(value.replace("Z", "+00:00"))
        except ValueError:
            return None
    return None


def _to_recollection(raw: dict[str, Any]) -> Recollection:
    """Map a mem0 result dict → Recollection. Tolerant of field absence."""
    return Recollection(
        text=str(raw.get("memory", raw.get("text", ""))),
        score=float(raw.get("score") or 0.0),
        source_id=str(raw.get("id", "")),
        when=_parse_when(raw.get("created_at") or raw.get("updated_at")),
        metadata={"source_backend": _SOURCE, **(raw.get("metadata") or {})},
    )


def _results_list(payload: Any) -> list[dict[str, Any]]:
    """mem0 search/get_all returns {"results": [...]} on newer builds, a bare list on older."""
    if isinstance(payload, dict):
        return list(payload.get("results", []))
    if isinstance(payload, list):
        return list(payload)
    return []


class Mem0Backend:
    """Adapter over ``mem0.Memory``. Inject a client for tests; build one otherwise."""

    declared_capabilities = set(_CAPS)

    def __init__(self, *, client: Any | None = None, config: dict | None = None) -> None:
        if client is not None:
            self._client = client
            return
        try:
            from mem0 import Memory  # noqa: PLC0415  (lazy: optional extra)
        except ImportError as exc:  # pragma: no cover - exercised only without the extra
            raise MissingExtraError("mem0") from exc
        self._client = Memory.from_config(config) if config else Memory()

    async def capabilities(self) -> set[Capability]:
        return set(_CAPS)

    async def remember(self, events: Sequence[MemoryEvent], scope: Scope) -> None:
        messages = [
            e if isinstance(e, dict) else {"role": "user", "content": event_text(e)} for e in events
        ]
        if not messages:
            return
        self._client.add(messages, **_scope_kwargs(scope))

    async def recall(self, query: str, scope: Scope, k: int = 10) -> list[Recollection]:
        payload = self._client.search(query=query, filters=_scope_kwargs(scope), top_k=k)
        return [_to_recollection(r) for r in _results_list(payload)]

    async def dump(self, scope: Scope) -> list[Recollection]:
        payload = self._client.get_all(filters=_scope_kwargs(scope))
        return [_to_recollection(r) for r in _results_list(payload)]

    async def ingest(self, items: Sequence[Recollection], scope: Scope) -> ExportReport:
        messages = [{"role": "user", "content": item.text} for item in items if item.text]
        if messages:
            self._client.add(messages, **_scope_kwargs(scope))
        return ExportReport.from_ingest(self, transferred=len(messages))
