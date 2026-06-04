"""AWM-style induction: turn a captured reasoning trace into a reusable Procedure.

HONEST SCOPE (do not overclaim): induce() is a trace-faithful, deterministic projection
of a trace's observed actions into the SAME Procedure data structure an author writes.
update() is a MANUAL hook applied when reality drifts — there is no background relearn,
no statistical generalization here. The novelty is that the output is data, so the engine
runs an induced flow on the exact same compile->run path as an authored one.

ReasoningTrace is a LOCAL minimal shape on purpose: no import of coactra.ai. Real
interop with coactra.ai's richer ReasoningTrace is an agent-layer wiring concern.
"""

from __future__ import annotations

from typing import Any

from pydantic import BaseModel, Field

from coactra.orchestration.workflow.domain.models import Procedure, Step


class ReasoningTrace(BaseModel):
    """A captured working path: the problem + the ordered actions that solved it.

    Each entry in `steps` is a dict with at least {"id": str, "kind": StepKind} plus any
    step-specific keys (condition/if_true/if_false/agent/reason). Minimal and local.
    """

    problem: str = Field(min_length=1)
    steps: list[dict[str, Any]] = Field(min_length=1)


def _to_steps(raw: list[dict[str, Any]]) -> list[Step]:
    steps: list[Step] = []
    for i, entry in enumerate(raw):
        nxt = raw[i + 1]["id"] if i + 1 < len(raw) and entry.get("kind") != "branch" else None
        # Branch entries carry their own targets; non-branch get the linear successor.
        data = {**entry}
        if entry.get("kind") != "branch" and "next" not in data:
            data["next"] = nxt
        steps.append(Step(**data))
    return steps


def induce(trace: ReasoningTrace) -> Procedure:
    """Project a trace into a runnable, induced Procedure (same type as authored)."""
    return Procedure(
        name=trace.problem,
        steps=_to_steps(trace.steps),
        is_induced=True,
    )


def update(procedure: Procedure, trace: ReasoningTrace) -> Procedure:
    """Manual drift hook: re-induce from a fresh trace, preserving the procedure name.

    Honest and minimal: this is a re-projection, not a merge/diff algorithm. The caller
    decides WHEN reality drifted; update() just produces the new induced Procedure.
    """
    fresh = induce(trace)
    return Procedure(name=procedure.name, steps=fresh.steps, is_induced=True)
