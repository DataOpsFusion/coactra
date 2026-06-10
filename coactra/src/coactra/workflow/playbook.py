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
    "VerificationReceipt",
    "ProofBundle",
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
    required_tags:
        Optional tag selectors used to disambiguate broad skills.
    approve:
        If True, the runner pauses here and waits for a human decision before
        executing this step.
    approval_only:
        If True, this is a pure human gate: no agent runs after approval.
    """

    instruction: str
    agent: str | None = None
    requires_skill: str | None = None
    required_tags: tuple[str, ...] = field(default_factory=tuple)
    approve: bool = False
    approval_only: bool = False

    def __post_init__(self) -> None:
        object.__setattr__(self, "required_tags", tuple(self.required_tags))
        if self.approval_only and not self.approve:
            raise ValueError("approval_only steps must also set approve=True")


def step(
    instruction: str,
    *,
    agent: str | None = None,
    requires_skill: str | None = None,
    required_tags: tuple[str, ...] | list[str] = (),
    approve: bool = False,
    approval_only: bool = False,
) -> Step:
    """Build a :class:`Step`. Instruction-first, keyword-only options."""
    return Step(
        instruction=instruction,
        agent=agent,
        requires_skill=requires_skill,
        required_tags=tuple(required_tags),
        approve=approve,
        approval_only=approval_only,
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
                    "required_tags": list(s.required_tags),
                    "approve": s.approve,
                    "approval_only": s.approval_only,
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
                required_tags=tuple(s.get("required_tags", ())),
                approve=bool(s.get("approve", False)),
                approval_only=bool(s.get("approval_only", False)),
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


@dataclass(frozen=True)
class VerificationReceipt:
    """Machine-checkable evidence that a verifier actually ran a check."""

    command: str
    exit_code: int
    stdout_sha256: str = ""
    stderr_sha256: str = ""
    artifact_paths: tuple[str, ...] = field(default_factory=tuple)

    def __post_init__(self) -> None:
        object.__setattr__(self, "artifact_paths", tuple(self.artifact_paths))


@dataclass(frozen=True)
class ProofBundle:
    """Evidence bundle attached to a human approval decision."""

    summary: str = ""
    receipts: tuple[VerificationReceipt, ...] = field(default_factory=tuple)
    artifact_paths: tuple[str, ...] = field(default_factory=tuple)

    def __post_init__(self) -> None:
        object.__setattr__(self, "receipts", tuple(self.receipts))
        object.__setattr__(self, "artifact_paths", tuple(self.artifact_paths))


@dataclass
class Approval:
    """Record of a human decision on an approve=True step."""

    step_index: int
    instruction: str
    decision: bool
    proof_bundle: ProofBundle | None = None


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
