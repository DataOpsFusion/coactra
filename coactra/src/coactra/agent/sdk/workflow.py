"""Core Workflow — pure-data Playbook + runner over Team.

Public API
----------
- ``step``         — helper that builds a :class:`Step` (instruction-first).
- ``Step``         — frozen dataclass: instruction, agent, needs, approve.
- ``Playbook``     — definition: name + list[Step].  to_dict/from_dict/from_yaml.
- ``StepResult``   — run ledger entry: instruction, agent, output, status.
- ``Approval``     — record of a human decision on an approve=True step.
- ``WorkflowRun``  — run instance: status, results ledger, pending_index.
- ``Workflow``     — runner: run(team) / resume(run, team, decision=).

No pydantic-ai imports at module level.  Duck-types team and agent.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

__all__ = [
    "step",
    "Step",
    "Playbook",
    "StepResult",
    "Approval",
    "WorkflowRun",
    "Workflow",
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
    def from_dict(cls, d: dict) -> "Playbook":
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
    def from_yaml(cls, text: str) -> "Playbook":
        """Parse a YAML string into a :class:`Playbook`.

        ``pyyaml`` is imported lazily so the module stays import-light.
        """
        import yaml  # noqa: PLC0415 — lazy import to keep module light

        data = yaml.safe_load(text)
        return cls.from_dict(data)


# ---------------------------------------------------------------------------
# Run ledger types
# ---------------------------------------------------------------------------

@dataclass
class StepResult:
    """A single entry in the run ledger."""

    instruction: str
    agent: str          # resolved agent name; "" if unresolved
    output: str         # agent output; "" if not run
    status: str         # "done" | "failed" | "skipped"


@dataclass
class Approval:
    """Record of a human decision on an approve=True step."""

    step_index: int
    instruction: str
    decision: bool      # True = approved, False = denied


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


# ---------------------------------------------------------------------------
# Workflow — the runner
# ---------------------------------------------------------------------------

class Workflow:
    """Runner for a :class:`Playbook` over a :class:`Team`.

    Parameters
    ----------
    name:
        Workflow / playbook name.
    steps:
        Ordered list of :class:`Step` objects.
    """

    def __init__(self, name: str, steps: list[Step]) -> None:
        self._playbook = Playbook(name=name, steps=list(steps))

    # ------------------------------------------------------------------
    # Constructors
    # ------------------------------------------------------------------

    @classmethod
    def from_playbook(cls, pb: Playbook) -> "Workflow":
        """Wrap an existing :class:`Playbook`."""
        return cls(pb.name, pb.steps)

    @classmethod
    def from_yaml(cls, text: str) -> "Workflow":
        """Parse YAML into a :class:`Playbook` and wrap it."""
        pb = Playbook.from_yaml(text)
        return cls.from_playbook(pb)

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _resolve_agent(self, s: Step, team: Any) -> Any | None:
        """Resolve a Step to a team member.  Name-pin wins over needs-routing."""
        if s.agent is not None:
            return team.member(s.agent)
        if s.needs is not None:
            return team.match(s.needs)
        return None

    # ------------------------------------------------------------------
    # run
    # ------------------------------------------------------------------

    async def run(
        self,
        team: Any,
        *,
        start: int = 0,
        ledger: list[StepResult] | None = None,
        approvals: list[Approval] | None = None,
    ) -> WorkflowRun:
        """Run the playbook from *start* over *team*.

        Parameters
        ----------
        team:
            A :class:`~coactra.agent.sdk.team.Team` (duck-typed: needs
            ``.member(name)`` and ``.match(needs)``).
        start:
            Step index to begin from.  Used by :meth:`resume` to continue
            after an interruption.
        ledger:
            Accumulated :class:`StepResult` list from a prior partial run.
            Mutated (a copy is taken) so the caller's list is not affected.
        approvals:
            Accumulated :class:`Approval` records from a prior run.

        Returns
        -------
        :class:`WorkflowRun`
        """
        results: list[StepResult] = list(ledger) if ledger else []
        approval_log: list[Approval] = list(approvals) if approvals else []
        steps = self._playbook.steps

        for i in range(start, len(steps)):
            s = steps[i]

            # Resolve agent first (before checking approve flag)
            agent = self._resolve_agent(s, team)
            if agent is None:
                results.append(StepResult(
                    instruction=s.instruction,
                    agent="",
                    output="",
                    status="failed",
                ))
                return WorkflowRun(
                    name=self._playbook.name,
                    status="failed",
                    results=results,
                    pending_index=None,
                    approvals=approval_log,
                    _steps=steps,
                )

            # Pause for approval before running the step
            if s.approve:
                return WorkflowRun(
                    name=self._playbook.name,
                    status="interrupted",
                    results=results,
                    pending_index=i,
                    approvals=approval_log,
                    _steps=steps,
                )

            # Run the step
            output = await agent.run(s.instruction)
            results.append(StepResult(
                instruction=s.instruction,
                agent=agent._name,
                output=str(output),
                status="done",
            ))

        return WorkflowRun(
            name=self._playbook.name,
            status="completed",
            results=results,
            pending_index=None,
            approvals=approval_log,
            _steps=steps,
        )

    # ------------------------------------------------------------------
    # resume
    # ------------------------------------------------------------------

    async def resume(
        self,
        run: WorkflowRun,
        team: Any,
        *,
        decision: bool,
    ) -> WorkflowRun:
        """Continue an interrupted run.

        Parameters
        ----------
        run:
            The :class:`WorkflowRun` returned by a previous :meth:`run` call
            with ``status="interrupted"``.
        team:
            The same :class:`~coactra.agent.sdk.team.Team` used for routing.
        decision:
            ``True`` → approve and run the pending step, then continue.
            ``False`` → deny the pending step, record it as skipped, stop.

        Returns
        -------
        :class:`WorkflowRun`
        """
        if run.status != "interrupted" or run.pending_index is None:
            raise ValueError(
                f"resume() requires an interrupted run; got status={run.status!r}"
            )

        steps = self._playbook.steps
        i = run.pending_index
        s = steps[i]

        # Copy accumulated ledger and approvals (don't mutate the original run)
        results: list[StepResult] = list(run.results)
        approval_log: list[Approval] = list(run.approvals)

        # Resolve agent for the pending step
        agent = self._resolve_agent(s, team)
        if agent is None:
            results.append(StepResult(
                instruction=s.instruction,
                agent="",
                output="",
                status="failed",
            ))
            return WorkflowRun(
                name=self._playbook.name,
                status="failed",
                results=results,
                pending_index=None,
                approvals=approval_log,
                _steps=steps,
            )

        if not decision:
            # Denied — record approval and skip the step
            approval_log.append(Approval(
                step_index=i,
                instruction=s.instruction,
                decision=False,
            ))
            results.append(StepResult(
                instruction=s.instruction,
                agent=agent._name,
                output="",
                status="skipped",
            ))
            return WorkflowRun(
                name=self._playbook.name,
                status="denied",
                results=results,
                pending_index=None,
                approvals=approval_log,
                _steps=steps,
            )

        # Approved — run the pending step
        approval_log.append(Approval(
            step_index=i,
            instruction=s.instruction,
            decision=True,
        ))
        output = await agent.run(s.instruction)
        results.append(StepResult(
            instruction=s.instruction,
            agent=agent._name,
            output=str(output),
            status="done",
        ))

        # Continue with remaining steps
        return await self.run(
            team,
            start=i + 1,
            ledger=results,
            approvals=approval_log,
        )
