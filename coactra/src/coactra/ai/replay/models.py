"""Procedural-memory record + decision types."""

from __future__ import annotations

import enum
from dataclasses import dataclass

from pydantic import BaseModel, Field


class Decision(enum.StrEnum):
    REPLAY = "replay"
    RE_REASON = "re_reason"


class ReasoningTrace(BaseModel):
    """One captured reasoning path. Quality is learned from replay outcomes."""

    id: str
    problem: str
    reasoning: str
    embedding: list[float]
    successes: int = 0
    failures: int = 0
    meta: dict = Field(default_factory=dict)

    @property
    def quality(self) -> float:
        """Laplace-smoothed success rate; neutral 0.5 prior with no data."""
        return (self.successes + 1) / (self.successes + self.failures + 2)

    def record(self, success: bool) -> None:
        if success:
            self.successes += 1
        else:
            self.failures += 1


@dataclass
class RecallResult:
    decision: Decision
    answer: str
    trace_id: str | None
    confidence: float
    reasoned_fresh: bool
