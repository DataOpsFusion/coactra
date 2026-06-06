"""Core Workflow — pure-data Playbook + runner over Team.

Public API
----------
- ``step``         — helper that builds a :class:`Step` (instruction-first).
- ``Step``         — frozen dataclass: instruction, agent, needs, approve.
- ``Playbook``     — definition: name + list[Step].  to_dict/from_dict/from_yaml.
- ``StepResult``   — run ledger entry: instruction, agent, output, status.
- ``Approval``     — record of a human decision on an approve=True step.
- ``WorkflowRun``  — run instance: status, results ledger, pending_index.
- ``Workflow``     — runner: run(team) / resume(run, team, decision=) /
                     run_goal(goal, team, ...) / resume_from(checkpoint, run_id, ...).

No pydantic-ai imports at module level.  Duck-types team and agent.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from coactra.agent.checkpoint import CheckpointStore
    from coactra.agent.playbook_store import PlaybookStore

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
        checkpoint: CheckpointStore | None = None,
        run_id: str | None = None,
    ) -> WorkflowRun:
        """Run the playbook from *start* over *team*.

        Parameters
        ----------
        team:
            A :class:`~coactra.agent.team.Team` (duck-typed: needs
            ``.member(name)`` and ``.match(needs)``).
        start:
            Step index to begin from.  Used by :meth:`resume` to continue
            after an interruption.
        ledger:
            Accumulated :class:`StepResult` list from a prior partial run.
            Mutated (a copy is taken) so the caller's list is not affected.
        approvals:
            Accumulated :class:`Approval` records from a prior run.
        checkpoint:
            Optional :class:`~coactra.agent.checkpoint.CheckpointStore`.  When
            provided (together with *run_id*), the run state is saved after each
            completed step and at every interrupt/failure return point.
        run_id:
            Stable identifier for this run.  Required when *checkpoint* is
            provided so successive saves target the same key.

        Returns
        -------
        :class:`WorkflowRun`
        """
        results: list[StepResult] = list(ledger) if ledger else []
        approval_log: list[Approval] = list(approvals) if approvals else []
        steps = self._playbook.steps

        def _save(run: WorkflowRun) -> None:
            """Persist *run* if a checkpoint store + run_id are present."""
            if checkpoint is not None and run_id is not None:
                from coactra.agent.checkpoint import run_to_state  # noqa: PLC0415
                checkpoint.save(run_id, run_to_state(run))

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
                final = WorkflowRun(
                    name=self._playbook.name,
                    status="failed",
                    results=results,
                    pending_index=None,
                    approvals=approval_log,
                    _steps=steps,
                )
                _save(final)
                return final

            # Pause for approval before running the step
            if s.approve:
                interrupted = WorkflowRun(
                    name=self._playbook.name,
                    status="interrupted",
                    results=results,
                    pending_index=i,
                    approvals=approval_log,
                    _steps=steps,
                )
                _save(interrupted)
                return interrupted

            # Run the step
            output = await agent.run(s.instruction)
            results.append(StepResult(
                instruction=s.instruction,
                agent=agent._name,
                output=str(output),
                status="done",
            ))

            # Save an intermediate snapshot after each completed step
            _save(WorkflowRun(
                name=self._playbook.name,
                status="running",
                results=list(results),
                pending_index=None,
                approvals=list(approval_log),
                _steps=steps,
            ))

        completed = WorkflowRun(
            name=self._playbook.name,
            status="completed",
            results=results,
            pending_index=None,
            approvals=approval_log,
            _steps=steps,
        )
        _save(completed)
        return completed

    # ------------------------------------------------------------------
    # resume
    # ------------------------------------------------------------------

    async def resume(
        self,
        run: WorkflowRun,
        team: Any,
        *,
        decision: bool,
        checkpoint: CheckpointStore | None = None,
        run_id: str | None = None,
    ) -> WorkflowRun:
        """Continue an interrupted run.

        Parameters
        ----------
        run:
            The :class:`WorkflowRun` returned by a previous :meth:`run` call
            with ``status="interrupted"``.
        team:
            The same :class:`~coactra.agent.team.Team` used for routing.
        decision:
            ``True`` → approve and run the pending step, then continue.
            ``False`` → deny the pending step, record it as skipped, stop.
        checkpoint:
            Optional :class:`~coactra.agent.checkpoint.CheckpointStore` to
            persist run state after each step.
        run_id:
            Stable identifier matching the original run's checkpoint key.

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

        # Continue with remaining steps (thread checkpoint through)
        return await self.run(
            team,
            start=i + 1,
            ledger=results,
            approvals=approval_log,
            checkpoint=checkpoint,
            run_id=run_id,
        )

    # ------------------------------------------------------------------
    # resume_from — reconstruct from a checkpoint store and continue
    # ------------------------------------------------------------------

    async def resume_from(
        self,
        checkpoint: CheckpointStore,
        run_id: str,
        team: Any,
        *,
        decision: bool | None = None,
    ) -> WorkflowRun:
        """Reconstruct a run from a checkpoint store and continue it.

        Parameters
        ----------
        checkpoint:
            A :class:`~coactra.agent.checkpoint.CheckpointStore` that holds the
            previously saved run state.
        run_id:
            The key under which the state was saved.
        team:
            The :class:`~coactra.agent.team.Team` used for routing.
        decision:
            For runs that were ``"interrupted"`` at an approval step:
            ``True`` to approve, ``False`` to deny.  Pass ``None`` when
            the run was not interrupted (it will continue from the last
            completed step).

        Returns
        -------
        :class:`WorkflowRun`

        Raises
        ------
        ValueError
            When *run_id* is not found in the checkpoint store.
        """
        from coactra.agent.checkpoint import run_from_state  # noqa: PLC0415

        state = checkpoint.load(run_id)
        if state is None:
            raise ValueError(
                f"No checkpoint found for run_id={run_id!r}"
            )

        restored = run_from_state(state)
        # Reattach the playbook steps so pending_step works correctly
        restored._steps = self._playbook.steps

        if restored.status == "interrupted" and restored.pending_index is not None:
            if decision is None:
                raise ValueError(
                    "decision= must be provided when resuming an interrupted run"
                )
            return await self.resume(
                restored,
                team,
                decision=decision,
                checkpoint=checkpoint,
                run_id=run_id,
            )

        # Non-interrupted state — continue from after the last completed step
        start = len(restored.results)
        return await self.run(
            team,
            start=start,
            ledger=restored.results,
            approvals=restored.approvals,
            checkpoint=checkpoint,
            run_id=run_id,
        )

    # ------------------------------------------------------------------
    # run_goal — triage: store-hit or plan → run → save candidate
    # ------------------------------------------------------------------

    @classmethod
    async def run_goal(
        cls,
        goal: str,
        team: Any,
        *,
        store: PlaybookStore | None = None,
        client: Any = None,
    ) -> WorkflowRun:
        """Triage a *goal*: reuse a promoted playbook or plan a new one.

        Parameters
        ----------
        goal:
            Plain-language description of the goal to accomplish.
        team:
            A :class:`~coactra.agent.team.Team` for routing and planning.
        store:
            Optional :class:`~coactra.agent.playbook_store.PlaybookStore`.
            When provided, ``store.find(goal)`` is checked first.  If a
            promoted playbook is found it is run directly (no planning).
            If not found, a new playbook is planned and — only on a
            completed run — stored as a **CANDIDATE** (not auto-promoted).
        client:
            Injectable LLM client for :func:`~coactra.agent.planner.plan_playbook`.
            When ``None``, the default :class:`coactra.ai.Client` is used.

        Returns
        -------
        :class:`WorkflowRun`
        """
        from coactra.agent.planner import plan_playbook  # noqa: PLC0415

        # Triage: check the store for a promoted playbook
        if store is not None:
            pb = store.find(goal)
            if pb is not None:
                wf = cls.from_playbook(pb)
                return await wf.run(team)

        # Miss — plan a new playbook
        pb = plan_playbook(goal, team, client=client)
        wf = cls.from_playbook(pb)
        run = await wf.run(team)

        # Save as candidate ONLY if the run completed successfully
        if store is not None and run.status == "completed":
            store.save_candidate(pb)

        return run
