"""Default ReasoningStore: in-process, tenant-partitioned, bounded + quality-filtered."""
from __future__ import annotations

from coactra.ai.completion.embedding import rank_traces
from coactra.ai.replay.models import ReasoningTrace


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
        return rank_traces(vector, self._by_tenant.get(tenant, {}).values(), k, min_quality)
