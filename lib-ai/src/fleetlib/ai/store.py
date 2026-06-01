"""Default ReasoningStore: in-process, tenant-partitioned, bounded + quality-filtered."""
from __future__ import annotations

from fleetlib.ai.embedding import cosine
from fleetlib.ai.models import ReasoningTrace


class InMemoryStore:
    """The one working default. Swap via the ReasoningStore Protocol."""

    def __init__(self) -> None:
        self._by_tenant: dict[str, dict[str, ReasoningTrace]] = {}

    def put(self, tenant: str, trace: ReasoningTrace) -> None:
        self._by_tenant.setdefault(tenant, {})[trace.id] = trace

    def get(self, tenant: str, trace_id: str) -> ReasoningTrace | None:
        return self._by_tenant.get(tenant, {}).get(trace_id)

    def search(
        self, tenant: str, vector: list[float], k: int, min_quality: float
    ) -> list[tuple[ReasoningTrace, float]]:
        traces = self._by_tenant.get(tenant, {}).values()
        scored = [
            (t, cosine(vector, t.embedding))
            for t in traces
            if t.quality >= min_quality
        ]
        scored.sort(key=lambda pair: pair[1], reverse=True)
        return scored[:k]
