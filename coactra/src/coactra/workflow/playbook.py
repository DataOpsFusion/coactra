"""Workflow playbook DTOs and helpers.

This module owns the pure data model used by the public Workflow facade. Agent
runtime code consumes these types but does not define them.
"""

from __future__ import annotations

from dataclasses import dataclass, field

__all__ = [
    "step",
    "Step",
    "Playbook",
    "StepResult",
    "Approval",
    "WorkflowRun",
]


@dataclass(frozen=True)
class Step:
    """One step in a Playbook.

    Parameters
    ----------
    instruction:
        What the agent should do.
    agent:
        Pin to an agent by name. Name-pin wins over skill routing.
    requires_skill:
        Route by exact skill identifier: the Team selects an agent whose
        effective skills include this value.
    approve:
        If True, the runner pauses here and waits for a human decision before
        executing this step.
    """

    instruction: str
    agent: str | None = None
    requires_skill: str | None = None
    approve: bool = False


def step(
    instruction: str,
    *,
    agent: str | None = None,
    requires_skill: str | None = None,
    approve: bool = False,
) -> Step:
    """Build a :class:`Step`. Instruction-first, keyword-only options."""
    return Step(
        instruction=instruction,
        agent=agent,
        requires_skill=requires_skill,
        approve=approve,
    )


@dataclass
class Playbook:
    """A named list of steps. Canonical form is plain dict/YAML."""

    name: str
    steps: list[Step]

    def to_dict(self) -> dict:
        """Convert to a plain dict (JSON-serialisable)."""
        return {
            "name": self.name,
            "steps": [
                {
                    "instruction": s.instruction,
                    "agent": s.agent,
                    "requires_skill": s.requires_skill,
                    "approve": s.approve,
                }
                for s in self.steps
            ],
        }

    @classmethod
    def from_dict(cls, d: dict) -> Playbook:
        """Reconstruct a :class:`Playbook` from a plain dict."""
        steps = [
            Step(
                instruction=s["instruction"],
                agent=s.get("agent"),
                requires_skill=s.get("requires_skill"),
                approve=bool(s.get("approve", False)),
            )
            for s in d.get("steps", [])
        ]
        return cls(name=d["name"], steps=steps)

    @classmethod
    def from_yaml(cls, text: str) -> Playbook:
        """Parse a YAML string into a :class:`Playbook`."""
        try:
            import yaml
        except ImportError:
            from coactra.errors import MissingExtraError

            raise MissingExtraError(
                "Playbook.from_yaml() requires pyyaml; install with: pip install coactra[office]",
                extra="office",
            ) from None

        data = yaml.safe_load(text)
        return cls.from_dict(data)


@dataclass
class StepResult:
    """A single entry in the run ledger."""

    instruction: str
    agent: str
    output: str
    status: str


@dataclass
class Approval:
    """Record of a human decision on an approve=True step."""

    step_index: int
    instruction: str
    decision: bool


@dataclass
class WorkflowRun:
    """The result of one Workflow execution."""

    name: str
    status: str
    results: list[StepResult]
    pending_index: int | None = None
    approvals: list[Approval] = field(default_factory=list)
    _steps: list[Step] = field(default_factory=list, repr=False)
    thread_id: str | None = None

    @property
    def pending_step(self) -> Step | None:
        if self.pending_index is None:
            return None
        try:
            return self._steps[self.pending_index]
        except IndexError:
            return None

    def output_texts(self) -> list[str]:
        return [r.output for r in self.results if r.status == "done"]
