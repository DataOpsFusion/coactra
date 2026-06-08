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

# ---------------------------------------------------------------------------
# Step — frozen data (the definition unit)
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class Step:
    """One step in a Playbook.

    Parameters
    ----------
    instruction:
        What the agent should do.
    agent:
        Pin to an agent by name (mutually exclusive with *needs* in spirit,
        but both may be provided — name-pin wins).
    needs:
        Route by capability: the Team's capability matcher selects the best
        agent whose skills cover this need.
    approve:
        If True, the runner pauses here and waits for a human decision before
        executing this step.
    """

    instruction: str
    agent: str | None = None
    needs: str | None = None
    approve: bool = False


def step(
    instruction: str,
    *,
    agent: str | None = None,
    needs: str | None = None,
    approve: bool = False,
) -> Step:
    """Build a :class:`Step`.  Instruction-first, keyword-only options."""
    return Step(instruction=instruction, agent=agent, needs=needs, approve=approve)


# ---------------------------------------------------------------------------
# Playbook — the definition (pure data)
# ---------------------------------------------------------------------------


@dataclass
class Playbook:
    """A named list of steps.  Canonical form is plain dict/YAML.

    Parameters
    ----------
    name:
        Playbook identifier.
    steps:
        Ordered list of :class:`Step` objects.
    """

    name: str
    steps: list[Step]

    # ------------------------------------------------------------------
    # Serialisation
    # ------------------------------------------------------------------

    def to_dict(self) -> dict:
        """Convert to a plain dict (JSON-serialisable)."""
        return {
            "name": self.name,
            "steps": [
                {
                    "instruction": s.instruction,
                    "agent": s.agent,
                    "needs": s.needs,
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
                needs=s.get("needs"),
                approve=bool(s.get("approve", False)),
            )
            for s in d.get("steps", [])
        ]
        return cls(name=d["name"], steps=steps)

    @classmethod
    def from_yaml(cls, text: str) -> Playbook:
        """Parse a YAML string into a :class:`Playbook`.

        ``pyyaml`` is imported lazily so the module stays import-light.
        """
        try:
            import yaml  # noqa: PLC0415 — lazy import to keep module light
        except ImportError:
            from coactra.errors import MissingExtraError

            raise MissingExtraError(
                "Playbook.from_yaml() requires pyyaml; install with: pip install coactra[office]",
                extra="office",
            ) from None

        data = yaml.safe_load(text)
        return cls.from_dict(data)


# ---------------------------------------------------------------------------
# Run ledger types
# ---------------------------------------------------------------------------


@dataclass
class StepResult:
    """A single entry in the run ledger."""

    instruction: str
    agent: str  # resolved agent name; "" if unresolved
    output: str  # agent output; "" if not run
    status: str  # "done" | "failed" | "skipped"


@dataclass
class Approval:
    """Record of a human decision on an approve=True step."""

    step_index: int
    instruction: str
    decision: bool  # True = approved, False = denied


@dataclass
class WorkflowRun:
    """The result of one Workflow execution (complete, interrupted, or failed).

    Attributes
    ----------
    name:
        Playbook name.
    status:
        One of ``"completed"``, ``"interrupted"``, ``"failed"``, ``"denied"``.
    results:
        Ordered run ledger — one :class:`StepResult` per step that was
        attempted or skipped.
    pending_index:
        Index of the step that caused an interruption (approve=True pause).
        ``None`` when not interrupted.
    approvals:
        List of :class:`Approval` records for any approval decisions made.
    _steps:
        Internal reference to the full step list (for ``pending_step``).
    """

    name: str
    status: str
    results: list[StepResult]
    pending_index: int | None = None
    approvals: list[Approval] = field(default_factory=list)
    _steps: list[Step] = field(default_factory=list, repr=False)
    thread_id: str | None = None

    @property
    def pending_step(self) -> Step | None:
        """Return the Step awaiting approval, or ``None``."""
        if self.pending_index is None:
            return None
        try:
            return self._steps[self.pending_index]
        except IndexError:
            return None

    def output_texts(self) -> list[str]:
        """Return the output string from every 'done' step in order."""
        return [r.output for r in self.results if r.status == "done"]
