"""Adaptive (vCache-style) accept gate.

Not a static threshold: the similarity a candidate must clear is adjusted by the
candidate's *verified* track record. Proven traces (high quality) earn a lower bar;
traces that have failed must clear a higher bar. The boundary moves as outcomes
accumulate via ReasoningTrace.record(...)/quality.
"""
from __future__ import annotations

from coactra.ai.replay.models import ReasoningTrace


class AdaptiveGate:
    def __init__(
        self, base_threshold: float = 0.90, floor: float = 0.70, span: float = 0.20
    ) -> None:
        self.base_threshold = base_threshold
        self.floor = floor
        self.span = span

    def required(self, trace: ReasoningTrace) -> float:
        """Similarity bar for this trace. quality 0.5 -> base; ->1 lowers, ->0 raises."""
        # quality in [0,1]; shift = (quality - 0.5) * 2 * span, clamped to floor.
        adjusted = self.base_threshold - (trace.quality - 0.5) * 2.0 * self.span
        return max(self.floor, adjusted)

    def accept(self, similarity: float, trace: ReasoningTrace) -> bool:
        return similarity >= self.required(trace)

    def confidence(self, similarity: float, trace: ReasoningTrace) -> float:
        c = similarity * trace.quality
        return max(0.0, min(1.0, c))
