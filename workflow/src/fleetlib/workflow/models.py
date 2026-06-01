"""Procedure-as-data models.

A Procedure is an ordered list of typed Steps. The SAME type is used whether a human
authored the flow or induce() learned it from a trace (is_induced just records origin).
Step kinds are deliberately few: task / branch / approve / ask / escalate.
"""

from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel, Field, model_validator

StepKind = Literal["task", "branch", "approve", "ask", "escalate"]


class Step(BaseModel):
    """One node in a Procedure.

    task     — do work (the engine invokes the registered callable for this id).
    branch   — `condition` is a flat state key; truthy -> if_true, else if_false.
               (The default LangGraphEngine does `bool(state.get(condition))`. A richer
               expression evaluator is a future engine concern, not v1.)
    approve  — pause for an Approver decision (human gate).
    ask      — collaborate: ask another `agent` (a Collaborator handles the talk).
    escalate — raise up the org via an EscalationRouter until a decider resolves it.
    """

    id: str = Field(min_length=1)
    kind: StepKind
    next: str | None = None  # linear successor for non-branch steps (None = terminal)

    # branch-only
    condition: str | None = None
    if_true: str | None = None
    if_false: str | None = None

    # ask-only
    agent: str | None = None
    question: str | None = None  # what to ask the agent (falls back to a state dump if unset)

    # escalate-only
    reason: str | None = None

    @model_validator(mode="after")
    def _validate_kind(self) -> "Step":
        if self.kind == "branch":
            if not self.condition or self.if_true is None or self.if_false is None:
                raise ValueError("branch step requires condition, if_true, if_false")
        if self.kind == "ask" and not self.agent:
            raise ValueError("ask step requires an agent")
        return self


class Procedure(BaseModel):
    """An ordered, runnable, runtime-editable flow. Authored and induced share this type."""

    name: str = Field(min_length=1)
    steps: list[Step] = Field(min_length=1)
    is_induced: bool = False

    @property
    def entry(self) -> Step:
        return self.steps[0]

    def step(self, step_id: str) -> Step:
        for s in self.steps:
            if s.id == step_id:
                return s
        raise KeyError(step_id)


class RunResult(BaseModel):
    """Outcome of one engine run: final state output + the step ids actually visited."""

    output: dict[str, Any] = Field(default_factory=dict)
    path: list[str] = Field(default_factory=list)
