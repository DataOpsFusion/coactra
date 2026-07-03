"""The novel core: capture -> gate -> bounded retrieve -> replay-or-fallback.

Guardrails (all enforced here):
  1. ADAPTIVE gate (AdaptiveGate) — not a static threshold.
  2. BOUNDED + quality-filtered retrieval (store.search with k + min_quality).
  3. Explicit REPLAY vs RE-REASON fallback — three branches below.
Multi-tenant: `tenant` threads through every call; the store partitions on it.
"""

from __future__ import annotations

import uuid
from collections.abc import Callable
from typing import Any

from coactra.ai.replay.gate import AdaptiveGate
from coactra.ai.replay.models import Decision, ReasoningTrace, RecallResult

Reasoner = Callable[[str], str]
EmbeddingFn = Callable[[str], list[float]]


class ReasoningEngine:
    def __init__(
        self,
        store: Any,
        embed: EmbeddingFn,
        reasoner: Reasoner,
        *,
        gate: AdaptiveGate | None = None,
        k: int = 3,
        min_quality: float = 0.4,
    ) -> None:
        self.store = store
        self.embed = embed
        self.reasoner = reasoner
        self.gate = gate or AdaptiveGate()
        self.k = k
        self.min_quality = min_quality

    def capture(self, tenant: str, problem: str, reasoning: str, **meta) -> str:
        trace = ReasoningTrace(
            id=uuid.uuid4().hex,
            problem=problem,
            reasoning=reasoning,
            embedding=self.embed(problem),
            meta=meta,
        )
        self.store.put(tenant, trace)
        return trace.id

    def record_outcome(self, tenant: str, trace_id: str, success: bool) -> None:
        trace = self.store.get(tenant, trace_id)
        if trace is None:
            return
        trace.record(success)
        self.store.put(tenant, trace)  # persist updated stats

    def recall_or_reason(self, tenant: str, problem: str) -> RecallResult:
        vector = self.embed(problem)
        # Guard 2: bounded + quality-filtered retrieval.
        hits = self.store.search(tenant, vector, k=self.k, min_quality=self.min_quality)

        # Branch C: no quality candidate -> re-reason.
        if hits:
            trace, similarity = hits[0]
            # Branch A: adaptive gate accepts -> replay.
            if self.gate.accept(similarity, trace):
                # Outcome of this replay is reported later via record_outcome().
                return RecallResult(
                    decision=Decision.REPLAY,
                    answer=trace.reasoning,
                    trace_id=trace.id,
                    confidence=self.gate.confidence(similarity, trace),
                    reasoned_fresh=False,
                )
            # Branch B: candidate exists but gate rejects -> re-reason (fall through).

        fresh = self.reasoner(problem)
        new_id = self.capture(tenant, problem, fresh)
        return RecallResult(
            decision=Decision.RE_REASON,
            answer=fresh,
            trace_id=new_id,
            confidence=0.0,
            reasoned_fresh=True,
        )
