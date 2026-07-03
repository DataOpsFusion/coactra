"""Agent-side Workflow runner over Team.

Pure playbook DTOs (`Step`, `Playbook`, `StepResult`, `Approval`, `WorkflowRun`,
and `step`) are owned by `coactra.workflow.playbook` and re-exported here for
runner-local convenience. This module owns execution over a Team, checkpoint
bridging, and goal planning.

No pydantic-ai imports at module level. Duck-types team and agent.
"""

from __future__ import annotations

from contextlib import nullcontext
from enum import StrEnum
from typing import TYPE_CHECKING, Any, Literal

from pydantic import BaseModel, Field, model_validator

if TYPE_CHECKING:
    from coactra.agent.checkpoint import CheckpointStore
    from coactra.agent.playbook_store import PlaybookStore

__all__ = [
    "Workflow",
]



from coactra.workflow.playbook import (
    Approval,
    Playbook,
    ProofBundle,
    Step,
    StepResult,
    VerificationReceipt,
    WorkflowRun,
    step,
)


class CodeChangeRiskTier(StrEnum):
    low = "low"
    medium = "medium"
    high = "high"


class VerifierRequirement(StrEnum):
    required = "required"
    advisory = "advisory"


VerificationKind = Literal["command", "http", "state", "artifact", "manual"]
ReviewOutcome = Literal["approve", "request_changes", "escalate", "uncertain"]


class VerificationCheck(BaseModel):
    """One verification check a specialized verifier should assess."""

    id: str = Field(min_length=1)
    kind: VerificationKind
    instruction: str = Field(min_length=1)
    params: dict[str, Any] = Field(default_factory=dict)
    success: dict[str, Any] = Field(default_factory=dict)


class VerifierRole(BaseModel):
    """A verification dimension with its own routing and checks."""

    role: str = Field(min_length=1)
    skill: str | None = None
    agent: str | None = None
    required_tags: list[str] = Field(default_factory=list)
    requirement: VerifierRequirement = VerifierRequirement.required
    checks: list[VerificationCheck] = Field(default_factory=list)
    summary: str = ""

    @model_validator(mode="after")
    def _validate_target(self) -> VerifierRole:
        if not self.skill and not self.agent:
            raise ValueError("verifier role requires either skill or agent")
        if self.skill and self.agent:
            raise ValueError("verifier role cannot pin both skill and agent")
        if not self.checks:
            raise ValueError("verifier role requires at least one check")
        return self


class CodeChangeVerificationFinding(BaseModel):
    role: str
    requirement: VerifierRequirement
    passed: bool | None = None
    summary: str = ""
    receipts: list[VerificationReceipt] = Field(default_factory=list)
    failures: list[str] = Field(default_factory=list)
    advisory_notes: list[str] = Field(default_factory=list)


class CodeChangeVerificationBundle(BaseModel):
    risk_tier: CodeChangeRiskTier
    findings: list[CodeChangeVerificationFinding] = Field(default_factory=list)
    summary: str = ""


class CodeChangeReviewDecision(BaseModel):
    decision: ReviewOutcome
    summary: str = Field(min_length=1)
    risks: list[str] = Field(default_factory=list)
    missing_proof: list[str] = Field(default_factory=list)
    followups: list[str] = Field(default_factory=list)


class CodeChangeWorkflowPlan(BaseModel):
    model_config = {"arbitrary_types_allowed": True}

    workflow: Any
    risk_tier: CodeChangeRiskTier
    verifier_roles: list[VerifierRole] = Field(default_factory=list)
    requires_human_approval: bool = False
    verification_bundle_type: type[CodeChangeVerificationBundle] = CodeChangeVerificationBundle
    review_decision_type: type[CodeChangeReviewDecision] = CodeChangeReviewDecision


class _TeamCollaborator:
    """Adapter from workflow ask steps to the public Team roster."""

    def __init__(self, team: Any) -> None:
        self._team = team

    async def ask(self, agent: str, question: str, state: dict[str, Any]) -> str:
        member = self._team.member(agent)
        if member is None:
            return ""
        checker = getattr(self._team, "check_workflow_step", None)
        if checker is not None:
            step_id = str(state.get("_workflow_step_id", ""))
            step_index = -1
            if step_id.startswith("step_"):
                try:
                    step_index = int(step_id.split("_", 1)[1])
                except ValueError:
                    step_index = -1
            workflow_name = str(state.get("_workflow_name", "workflow"))
            synthetic = Step(instruction=question, agent=agent)
            decision = await checker(
                phase="execute",
                workflow_name=workflow_name,
                step_index=step_index,
                step=synthetic,
                agent_name=getattr(member, "_name", agent),
            )
            allowed = getattr(decision, "allowed", None)
            if not isinstance(allowed, bool):
                outcome = getattr(decision, "outcome", None)
                allowed = outcome == "allow" or str(outcome) == "DecisionOutcome.allow"
            if not allowed:
                raise PermissionError(
                    "policy denied workflow step "
                    f"{workflow_name}:{step_id or step_index} for agent {agent}"
                )
        return str(await member.run(question))


class _ApprovalSentinel:
    _name = "human:approval"


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

    @property
    def name(self) -> str:
        return self._playbook.name

    # ------------------------------------------------------------------
    # Constructors
    # ------------------------------------------------------------------

    @classmethod
    def from_playbook(cls, pb: Playbook) -> Workflow:
        """Wrap an existing :class:`Playbook`."""
        return cls(pb.name, pb.steps)

    @classmethod
    def from_yaml(cls, text: str) -> Workflow:
        """Parse YAML into a :class:`Playbook` and wrap it."""
        pb = Playbook.from_yaml(text)
        return cls.from_playbook(pb)

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _resolve_agent(self, s: Step, team: Any) -> Any | None:
        """Resolve a Step to a team member. Name-pin wins over skill routing."""
        if s.approval_only:
            return _ApprovalSentinel()
        if s.agent is not None:
            return team.member(s.agent)
        if s.requires_skill is not None:
            matcher = getattr(team, "match_skill", None)
            if matcher is None:
                return None
            try:
                return matcher(s.requires_skill, required_tags=s.required_tags)
            except TypeError:
                return matcher(s.requires_skill)
        return None

    @staticmethod
    def _decision_allowed(decision: Any) -> bool:
        allowed = getattr(decision, "allowed", None)
        if isinstance(allowed, bool):
            return allowed
        outcome = getattr(decision, "outcome", None)
        return outcome == "allow" or str(outcome) == "DecisionOutcome.allow"

    async def _policy_allows(
        self,
        team: Any,
        *,
        phase: str,
        step_index: int,
        step: Step,
        agent: Any,
    ) -> bool:
        checker = getattr(team, "check_workflow_step", None)
        if checker is None:
            return True
        decision = await checker(
            phase=phase,
            workflow_name=self._playbook.name,
            step_index=step_index,
            step=step,
            agent_name=getattr(agent, "_name", ""),
        )
        return self._decision_allowed(decision)

    async def _resolve_step_agent(self, team: Any, step_index: int, step: Step) -> Any | None:
        try:
            agent = self._resolve_agent(step, team)
        except ValueError:
            return None
        if agent is None:
            return None
        if not await self._policy_allows(
            team,
            phase="route",
            step_index=step_index,
            step=step,
            agent=agent,
        ):
            return None
        return agent

    @staticmethod
    def _coerce_proof_bundle(value: Any) -> ProofBundle | None:
        if value is None or isinstance(value, ProofBundle):
            return value
        if not isinstance(value, dict):
            raise TypeError("proof_bundle must be a ProofBundle, dict, or None")
        receipts = []
        for receipt in value.get("receipts", []):
            if isinstance(receipt, VerificationReceipt):
                receipts.append(receipt)
                continue
            receipts.append(
                VerificationReceipt(
                    command=receipt["command"],
                    exit_code=int(receipt["exit_code"]),
                    stdout_sha256=receipt.get("stdout_sha256", ""),
                    stderr_sha256=receipt.get("stderr_sha256", ""),
                    artifact_paths=tuple(receipt.get("artifact_paths", ())),
                )
            )
        return ProofBundle(
            summary=value.get("summary", ""),
            receipts=tuple(receipts),
            artifact_paths=tuple(value.get("artifact_paths", ())),
        )

    def _normalize_resume_decision(
        self,
        decision: bool | dict[str, Any],
        proof_bundle: ProofBundle | dict[str, Any] | None = None,
    ) -> tuple[bool, ProofBundle | None]:
        if isinstance(decision, dict):
            approved = bool(decision.get("approved", False))
            bundle = decision.get("proof_bundle", proof_bundle)
        else:
            approved = bool(decision)
            bundle = proof_bundle
        return approved, self._coerce_proof_bundle(bundle)

    # ------------------------------------------------------------------
    # durable engine bridge — delegate to coactra.workflow engines
    # ------------------------------------------------------------------

    def _tenant_for_team(self, team: Any) -> str:
        members = getattr(team, "_members", [])
        if isinstance(members, dict):
            members = list(members.values())
        for member in members:
            tenant = getattr(member, "_tenant", None)
            if tenant:
                return str(tenant)
        return "default"

    async def _resolve_steps_for_engine(
        self,
        team: Any,
    ) -> list[tuple[int, Step, Any]] | WorkflowRun:
        resolved: list[tuple[int, Step, Any]] = []
        for i, s in enumerate(self._playbook.steps):
            agent = await self._resolve_step_agent(team, i, s)
            if agent is None:
                return WorkflowRun(
                    name=self._playbook.name,
                    status="failed",
                    results=[StepResult(s.instruction, "", "", "failed")],
                    _steps=self._playbook.steps,
                )
            resolved.append((i, s, agent))
        return resolved

    def _to_procedure(self, resolved: list[tuple[int, Step, Any]]) -> Any:
        from coactra.workflow import Procedure  # noqa: PLC0415
        from coactra.workflow import Step as ProcedureStep

        def node_id(i: int) -> str:
            return f"step_{i}"

        def entry_id(i: int, s: Step) -> str:
            return f"approve_{i}" if s.approve else node_id(i)

        proc_steps: list[Any] = []
        for pos, (i, s, agent) in enumerate(resolved):
            next_id = (
                entry_id(resolved[pos + 1][0], resolved[pos + 1][1])
                if pos + 1 < len(resolved)
                else None
            )
            ask_id = node_id(i)
            if s.approval_only:
                proc_steps.append(ProcedureStep(id=f"approve_{i}", kind="approve", next=next_id))
                continue
            if s.approve:
                proc_steps.append(ProcedureStep(id=f"approve_{i}", kind="approve", next=ask_id))
            proc_steps.append(
                ProcedureStep(
                    id=ask_id,
                    kind="ask",
                    agent=getattr(agent, "_name", "") if agent is not None else "",
                    question=s.instruction,
                    next=next_id,
                )
            )
        return Procedure(name=self._playbook.name, steps=proc_steps)

    def _run_from_engine_snapshot(
        self, snapshot: Any, resolved: list[tuple[int, Step, Any]]
    ) -> WorkflowRun:
        from coactra.workflow import WorkflowRunStatus  # noqa: PLC0415

        state = getattr(snapshot, "state", {}) or {}
        results: list[StepResult] = []
        for i, s, agent in resolved:
            key = f"step_{i}_result"
            if key not in state:
                continue
            results.append(
                StepResult(
                    instruction=s.instruction,
                    agent=getattr(agent, "_name", "") if agent is not None else "",
                    output=str(state.get(key, "")),
                    status="done",
                )
            )

        status = getattr(snapshot, "status", None)
        if (
            status is WorkflowRunStatus.interrupted
            or str(status) == "WorkflowRunStatus.interrupted"
        ):
            pending_index = None
            interrupt = getattr(snapshot, "interrupt", None)
            step_id = getattr(interrupt, "step_id", "") if interrupt is not None else ""
            if step_id.startswith("approve_"):
                try:
                    pending_index = int(step_id.split("_", 1)[1])
                except ValueError:
                    pending_index = None
            return WorkflowRun(
                name=self._playbook.name,
                status="interrupted",
                results=results,
                pending_index=pending_index,
                _steps=self._playbook.steps,
                thread_id=getattr(snapshot, "thread_id", None),
            )

        if status is WorkflowRunStatus.failed or str(status) == "WorkflowRunStatus.failed":
            public_status = "failed"
        else:
            public_status = "completed"
        return WorkflowRun(
            name=self._playbook.name,
            status=public_status,
            results=results,
            _steps=self._playbook.steps,
            thread_id=getattr(snapshot, "thread_id", None),
        )

    async def _run_with_engine(
        self, team: Any, engine: Any, *, run_id: str | None, span: Any | None = None
    ) -> WorkflowRun:
        from coactra.workflow import RunContext, Scope  # noqa: PLC0415

        resolved = await self._resolve_steps_for_engine(team)
        if isinstance(resolved, WorkflowRun):
            return resolved
        procedure = self._to_procedure(resolved)
        ctx = RunContext(
            scope=Scope(tenant_id=self._tenant_for_team(team)),
            collaborator=_TeamCollaborator(team),
        )
        if span is not None:
            span.add_event("coactra.workflow.engine.start")
        snapshot = await engine.start(procedure, {}, ctx, thread_id=run_id)
        run = self._run_from_engine_snapshot(snapshot, resolved)
        if span is not None:
            span.add_event(
                "coactra.workflow.engine.complete",
                attributes={"coactra.workflow.status": run.status},
            )
        return run

    async def resume_engine(
        self,
        engine: Any,
        thread_id: str,
        team: Any,
        *,
        decision: bool | dict[str, Any] | None = None,
        state: dict[str, Any] | None = None,
    ) -> WorkflowRun:
        """Resume a run delegated to an old ``coactra.workflow`` engine."""
        from coactra.workflow import RunContext, Scope  # noqa: PLC0415

        resolved = await self._resolve_steps_for_engine(team)
        if isinstance(resolved, WorkflowRun):
            return resolved
        procedure = self._to_procedure(resolved)
        tenant = thread_id.split(":", 1)[0] if ":" in thread_id else self._tenant_for_team(team)
        ctx = RunContext(
            scope=Scope(tenant_id=tenant),
            collaborator=_TeamCollaborator(team),
        )
        resume_decision = {"approved": decision} if isinstance(decision, bool) else decision
        snapshot = await engine.resume(
            thread_id,
            ctx,
            procedure=procedure,
            decision=resume_decision,
            state=state,
        )
        return self._run_from_engine_snapshot(snapshot, resolved)

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
        engine: Any | None = None,
        tracer: Any | None = None,
    ) -> WorkflowRun:
        """Run the playbook from *start* over *team*.

        Parameters
        ----------
        team:
            A :class:`~coactra.team.Team` (duck-typed: exposes
            ``.member(name)`` and ``.match_skill(skill_id, required_tags=...)``).
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
        span_cm = (
            tracer.start_as_current_span(
                "coactra.workflow.run",
                attributes={
                    "coactra.workflow.name": self._playbook.name,
                    "coactra.run_id": run_id or "",
                },
            )
            if tracer is not None
            else nullcontext(None)
        )
        with span_cm as span:
            if engine is not None:
                if start != 0 or ledger is not None or approvals is not None:
                    raise ValueError(
                        "engine= runs must start from a fresh Workflow; use resume_engine()"
                    )
                return await self._run_with_engine(team, engine, run_id=run_id, span=span)

            return await self._run_local(
                team,
                start=start,
                ledger=ledger,
                approvals=approvals,
                checkpoint=checkpoint,
                run_id=run_id,
                span=span,
            )

    async def _run_local(
        self,
        team: Any,
        *,
        start: int,
        ledger: list[StepResult] | None,
        approvals: list[Approval] | None,
        checkpoint: CheckpointStore | None,
        run_id: str | None,
        span: Any | None,
    ) -> WorkflowRun:
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

            if span is not None:
                span.add_event(
                    "coactra.workflow.step.start",
                    attributes={
                        "coactra.workflow.step.index": i,
                        "coactra.workflow.step.instruction": s.instruction,
                    },
                )

            # Resolve and authorize the step before checking approve flag.
            agent = await self._resolve_step_agent(team, i, s)
            if agent is None:
                results.append(
                    StepResult(
                        instruction=s.instruction,
                        agent="",
                        output="",
                        status="failed",
                    )
                )
                final = WorkflowRun(
                    name=self._playbook.name,
                    status="failed",
                    results=results,
                    pending_index=None,
                    approvals=approval_log,
                    _steps=steps,
                )
                if span is not None:
                    span.add_event(
                        "coactra.workflow.step.fail",
                        attributes={"coactra.workflow.step.index": i},
                    )
                _save(final)
                return final

            if not await self._policy_allows(
                team,
                phase="execute",
                step_index=i,
                step=s,
                agent=agent,
            ):
                results.append(
                    StepResult(
                        instruction=s.instruction,
                        agent=getattr(agent, "_name", "") if agent is not None else "",
                        output="",
                        status="failed",
                    )
                )
                final = WorkflowRun(
                    name=self._playbook.name,
                    status="failed",
                    results=results,
                    pending_index=None,
                    approvals=approval_log,
                    _steps=steps,
                )
                if span is not None:
                    span.add_event(
                        "coactra.workflow.step.fail",
                        attributes={"coactra.workflow.step.index": i},
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
                if span is not None:
                    span.add_event(
                        "coactra.workflow.interrupt",
                        attributes={"coactra.workflow.step.index": i},
                    )
                _save(interrupted)
                return interrupted

            # Run the step
            output = await agent.run(s.instruction)
            results.append(
                StepResult(
                    instruction=s.instruction,
                    agent="" if s.approval_only else agent._name,
                    output=str(output),
                    status="done",
                )
            )
            if span is not None:
                span.add_event(
                    "coactra.workflow.step.complete",
                    attributes={
                        "coactra.workflow.step.index": i,
                        "coactra.agent.name": agent._name,
                    },
                )

            # Save an intermediate snapshot after each completed step
            _save(
                WorkflowRun(
                    name=self._playbook.name,
                    status="running",
                    results=list(results),
                    pending_index=None,
                    approvals=list(approval_log),
                    _steps=steps,
                )
            )

        completed = WorkflowRun(
            name=self._playbook.name,
            status="completed",
            results=results,
            pending_index=None,
            approvals=approval_log,
            _steps=steps,
        )
        if span is not None:
            span.add_event("coactra.workflow.complete")
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
        decision: bool | dict[str, Any],
        checkpoint: CheckpointStore | None = None,
        proof_bundle: ProofBundle | dict[str, Any] | None = None,
        run_id: str | None = None,
    ) -> WorkflowRun:
        """Continue an interrupted run.

        Parameters
        ----------
        run:
            The :class:`WorkflowRun` returned by a previous :meth:`run` call
            with ``status="interrupted"``.
        team:
            The same :class:`~coactra.team.Team` used for routing.
        decision:
            ``True`` or ``{"approved": True, "proof_bundle": ...}`` approves the
            pending step and continues. ``False`` denies the step and records
            it as skipped.
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
            raise ValueError(f"resume() requires an interrupted run; got status={run.status!r}")

        steps = self._playbook.steps

        def _save(resumed: WorkflowRun) -> None:
            if checkpoint is not None and run_id is not None:
                from coactra.agent.checkpoint import run_to_state  # noqa: PLC0415

                checkpoint.save(run_id, run_to_state(resumed))

        i = run.pending_index
        s = steps[i]

        # Copy accumulated ledger and approvals (don't mutate the original run)
        results: list[StepResult] = list(run.results)
        approval_log: list[Approval] = list(run.approvals)

        # Resolve agent for the pending step
        agent = await self._resolve_step_agent(team, i, s)
        if agent is None:
            results.append(
                StepResult(
                    instruction=s.instruction,
                    agent="",
                    output="",
                    status="failed",
                )
            )
            failed = WorkflowRun(
                name=self._playbook.name,
                status="failed",
                results=results,
                pending_index=None,
                approvals=approval_log,
                _steps=steps,
            )
            _save(failed)
            return failed

        approved, approved_bundle = self._normalize_resume_decision(decision, proof_bundle)

        if not approved:
            # Denied — record approval and skip the step
            approval_log.append(
                Approval(
                    step_index=i,
                    instruction=s.instruction,
                    decision=False,
                    proof_bundle=approved_bundle,
                )
            )
            results.append(
                StepResult(
                    instruction=s.instruction,
                    agent="" if s.approval_only else agent._name,
                    output="",
                    status="skipped",
                )
            )
            denied = WorkflowRun(
                name=self._playbook.name,
                status="denied",
                results=results,
                pending_index=None,
                approvals=approval_log,
                _steps=steps,
            )
            _save(denied)
            return denied

        if approved_bundle is None:
            raise ValueError("approved workflow steps require proof_bundle evidence")
        if not await self._policy_allows(
            team,
            phase="execute",
            step_index=i,
            step=s,
            agent=agent,
        ):
            results.append(
                StepResult(
                    instruction=s.instruction,
                    agent=getattr(agent, "_name", "") if agent is not None else "",
                    output="",
                    status="failed",
                )
            )
            failed = WorkflowRun(
                name=self._playbook.name,
                status="failed",
                results=results,
                pending_index=None,
                approvals=approval_log,
                _steps=steps,
            )
            _save(failed)
            return failed

        # Approved — record the approval and, unless this is a pure gate, run the step.
        approval_log.append(
            Approval(
                step_index=i,
                instruction=s.instruction,
                decision=True,
                proof_bundle=approved_bundle,
            )
        )
        if not s.approval_only:
            output = await agent.run(s.instruction)
            results.append(
                StepResult(
                    instruction=s.instruction,
                    agent=agent._name,
                    output=str(output),
                    status="done",
                )
            )

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
        decision: bool | dict[str, Any] | None = None,
        proof_bundle: ProofBundle | dict[str, Any] | None = None,
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
            The :class:`~coactra.team.Team` used for routing.
        decision:
            For runs that were ``"interrupted"`` at an approval step:
            ``True`` or ``{"approved": True, "proof_bundle": ...}`` to approve,
            ``False`` to deny. Pass ``None`` when
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
            raise ValueError(f"No checkpoint found for run_id={run_id!r}")

        restored = run_from_state(state)
        # Reattach the playbook steps so pending_step works correctly
        restored._steps = self._playbook.steps

        if restored.status == "interrupted" and restored.pending_index is not None:
            if decision is None:
                raise ValueError("decision= must be provided when resuming an interrupted run")
            return await self.resume(
                restored,
                team,
                decision=decision,
                checkpoint=checkpoint,
                run_id=run_id,
                proof_bundle=proof_bundle,
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


    @staticmethod
    def _code_change_verifier_instruction(role: VerifierRole) -> str:
        lines = [
            f"Act as the {role.role} verifier for this code or operations change.",
            f"Requirement level: {role.requirement.value}.",
        ]
        if role.summary:
            lines.append(role.summary)
        lines.append(
            "Collect evidence for every check you can safely run and "
            "aggregate failures instead of failing fast."
        )
        for check in role.checks:
            lines.append(
                f"- [{check.kind}] {check.id}: {check.instruction}"
            )
        return "\n".join(lines)

    @staticmethod
    def _code_change_review_instruction(
        risk_tier: CodeChangeRiskTier,
        verifier_roles: list[VerifierRole],
    ) -> str:
        roles = ", ".join(
            f"{role.role}({role.requirement.value})" for role in verifier_roles
        ) or "none"
        return (
            "Review the implementation and the verifier evidence bundle. "
            "Return a structured review decision with one of: approve, "
            "request_changes, escalate, uncertain. "
            f"Risk tier: {risk_tier.value}. Verification coverage: {roles}."
        )

    @classmethod
    def code_change(
        cls,
        name: str,
        *,
        implement_instruction: str,
        verifier_roles: list[VerifierRole],
        implement_skill: str | None = None,
        implement_agent: str | None = None,
        implement_tags: tuple[str, ...] | list[str] = (),
        review_skill: str | None = None,
        review_agent: str | None = None,
        review_tags: tuple[str, ...] | list[str] = (),
        reviewer_instruction: str | None = None,
        risk_tier: CodeChangeRiskTier = CodeChangeRiskTier.medium,
        human_approval: Literal["auto", "always", "never"] = "auto",
    ) -> CodeChangeWorkflowPlan:
        """Build a thin implement -> verify* -> review -> optional human approval workflow."""
        if not implement_skill and not implement_agent:
            raise ValueError("code_change requires either implement_skill or implement_agent")
        if implement_skill and implement_agent:
            raise ValueError("code_change implement target cannot pin both skill and agent")
        if not review_skill and not review_agent:
            raise ValueError("code_change requires either review_skill or review_agent")
        if review_skill and review_agent:
            raise ValueError("code_change review target cannot pin both skill and agent")
        if not verifier_roles:
            raise ValueError("code_change requires at least one verifier role")

        steps: list[Step] = [
            step(
                implement_instruction,
                agent=implement_agent,
                requires_skill=implement_skill,
                required_tags=tuple(implement_tags),
            )
        ]
        for role in verifier_roles:
            steps.append(
                step(
                    cls._code_change_verifier_instruction(role),
                    agent=role.agent,
                    requires_skill=role.skill,
                    required_tags=tuple(role.required_tags),
                )
            )
        steps.append(
            step(
                reviewer_instruction
                or cls._code_change_review_instruction(risk_tier, verifier_roles),
                agent=review_agent,
                requires_skill=review_skill,
                required_tags=tuple(review_tags),
            )
        )
        needs_human = human_approval == "always" or (
            human_approval == "auto" and risk_tier is not CodeChangeRiskTier.low
        )
        if needs_human:
            steps.append(
                step(
                    "Human approval for reviewed change "
                    f"({risk_tier.value} risk). Approve the proof bundle.",
                    approve=True,
                    approval_only=True,
                )
            )
        return CodeChangeWorkflowPlan(
            workflow=cls(name, steps=steps),
            risk_tier=risk_tier,
            verifier_roles=verifier_roles,
            requires_human_approval=needs_human,
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
            A :class:`~coactra.team.Team` for routing and planning.
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
