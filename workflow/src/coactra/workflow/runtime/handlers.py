"""The injected seams for the three non-task step kinds.

workflow owns WHEN/WHAT (it raises these and calls these handlers); it does NOT own who
the chain is (organization) or how the talk happens (agent). So approve/ask/escalate are
Protocols with trivial, honest in-process defaults. Swap in real org routing / A2A talk /
interrupt()-based human gates at the agent layer.
"""

from __future__ import annotations

from typing import Any, Protocol, runtime_checkable

from pydantic import BaseModel, Field


class EscalationUnresolved(RuntimeError):
    """Raised when an escalation reaches the top of the chain without a decider."""


class Escalation(BaseModel):
    """A workflow's signal that it cannot decide on its own and must go up the org."""

    reason: str
    state: dict[str, Any] = Field(default_factory=dict)


@runtime_checkable
class Approver(Protocol):
    def approve(self, step_id: str, state: dict[str, Any]) -> bool:
        """Decide whether an `approve` step may proceed."""
        ...


@runtime_checkable
class Collaborator(Protocol):
    def ask(self, agent: str, question: str, state: dict[str, Any]) -> str:
        """Carry an `ask` step to another agent and return its answer."""
        ...


@runtime_checkable
class EscalationRouter(Protocol):
    def route(self, escalation: Escalation, chain: list[str]) -> str:
        """Walk an escalation UP `chain` and return the id of the decider that resolved it."""
        ...


class AutoApprove:
    """Default Approver — green-lights everything (for tests / fully-trusted flows)."""

    def approve(self, step_id: str, state: dict[str, Any]) -> bool:
        return True


class RejectAll:
    """Default Approver alt — denies everything (proves the gate actually gates)."""

    def approve(self, step_id: str, state: dict[str, Any]) -> bool:
        return False


class NullCollaborator:
    """Default Collaborator — returns a pre-recorded answer per agent; no real wire."""

    def __init__(self, answers: dict[str, str] | None = None) -> None:
        self._answers = answers or {}

    def ask(self, agent: str, question: str, state: dict[str, Any]) -> str:
        return self._answers.get(agent, "")


class TerminalHumanRouter:
    """Default EscalationRouter — the chain is opaque to workflow; this just takes the
    LAST id in the provided chain as the terminal decider (human / SOTA). Real hierarchy
    walking lives in `organization`; workflow holds NO org logic of its own."""

    def route(self, escalation: Escalation, chain: list[str]) -> str:
        if not chain:
            raise EscalationUnresolved(escalation.reason)
        return chain[-1]
