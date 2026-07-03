"""Default ReasoningStore: in-process, tenant-partitioned, bounded + quality-filtered."""

from __future__ import annotations

import math
from collections.abc import Iterable

from coactra.ai.replay.models import ReasoningTrace


def _cosine(a: list[float], b: list[float]) -> float:
    dot = sum(x * y for x, y in zip(a, b, strict=False))
    na = math.sqrt(sum(x * x for x in a))
    nb = math.sqrt(sum(y * y for y in b))
    return 0.0 if na == 0.0 or nb == 0.0 else dot / (na * nb)


def _rank_traces(
    query: list[float],
    candidates: Iterable[ReasoningTrace],
    k: int,
    min_quality: float,
) -> list[tuple[ReasoningTrace, float]]:
    scored = [
        (trace, _cosine(query, trace.embedding))
        for trace in candidates
        if trace.quality >= min_quality
    ]
    scored.sort(key=lambda pair: pair[1], reverse=True)
    return scored[:k]


class InMemoryStore:
    """The one working default."""

    def __init__(self) -> None:
        self._by_tenant: dict[str, dict[str, ReasoningTrace]] = {}

    def put(self, tenant: str, trace: ReasoningTrace) -> None:
        self._by_tenant.setdefault(tenant, {})[trace.id] = trace

    def get(self, tenant: str, trace_id: str) -> ReasoningTrace | None:
        return self._by_tenant.get(tenant, {}).get(trace_id)

    def search(
        self, tenant: str, vector: list[float], k: int, min_quality: float
    ) -> list[tuple[ReasoningTrace, float]]:
        return _rank_traces(vector, self._by_tenant.get(tenant, {}).values(), k, min_quality)
