"""Reference facade joining durable work orders to reusable procedures."""

from __future__ import annotations

from collections.abc import Callable
from typing import Any

from pydantic import BaseModel

from coactra.scope import Scope
from coactra.workflow import (
    InMemoryProcedureStore,
    PendingApproval,
    Procedure,
    ProcedureRunner,
    ProcedureStore,
    RunContext,
    RunResult,
    WorkflowEngine,
    WorkflowRun,
    WorkflowRunStatus,
    make_default_workflow_engine,
)
from coactra.workflow.ledger import (
    Decision,
    DecisionOutcome,
    Lease,
    WorkManager,
    WorkOrder,
    WorkStatus,
)
from coactra.workflow.runtime.approval import ApprovalStore, InMemoryApprovalStore


class ProcedureNotFoundError(LookupError):
    """Raised when a work order names a procedure that is not registered in scope."""


class WorkflowEngineRequiredError(RuntimeError):
    """Raised when procedure execution is requested without an injected engine."""


class OrchestrationResult(BaseModel):
    """Combined result for one simple procedure-backed work-order execution."""

    order: WorkOrder
    run: RunResult


class Orchestrator:
    """Small composition facade over the work ledger and an injected workflow engine.

    This reference facade is intentionally synchronous because the current procedure
    engine seam is synchronous. Production runtimes such as Temporal, DBOS, Dapr, or the
    existing homelab workflow runtime remain external dispatch targets.
    """

    def __init__(
        self,
        work: WorkManager | None = None,
        *,
        procedures: ProcedureStore | None = None,
        engine: ProcedureRunner | None = None,
        context_factory: Callable[[Scope], RunContext] | None = None,
    ) -> None:
        self.work = work or WorkManager()
        self.procedures = procedures or InMemoryProcedureStore()
        self.engine = engine
        self.context_factory = context_factory or (lambda scope: RunContext(scope=scope))

    def submit(self, order: WorkOrder) -> WorkOrder:
        return self.work.submit(order)

    def register(self, procedure: Procedure, scope: Scope) -> None:
        self.procedures.save(procedure, scope)

    def run(
        self,
        work_id: str,
        scope: Scope,
        *,
        worker: str,
        state: dict[str, Any] | None = None,
        lease_seconds: int = 300,
    ) -> OrchestrationResult:
        if self.engine is None:
            raise WorkflowEngineRequiredError("procedure execution requires an injected engine")
        order = self.work.get(work_id, scope)
        if not order.procedure:
            raise ProcedureNotFoundError("work order does not name a procedure")
        procedure = self.procedures.get(order.procedure, scope)
        if procedure is None:
            raise ProcedureNotFoundError(
                f"procedure {order.procedure!r} not found in scope {scope.key!r}"
            )
        lease = self.work.claim(work_id, scope, worker=worker, lease_seconds=lease_seconds)
        self.work.start(lease, scope)
        try:
            run = self.engine.run(procedure, state or {}, self.context_factory(scope))
        except Exception as exc:
            self.work.fail(lease, scope, error=str(exc), retry=False)
            raise
        completed = self.work.complete(lease, scope)
        return OrchestrationResult(order=completed, run=run)

    def cancel(self, work_id: str, scope: Scope, *, reason: str = "") -> WorkOrder:
        return self.work.cancel(work_id, scope, reason=reason)


class DurableOrchestrationResult(BaseModel):
    """Work-order view of one async durable-engine transition."""

    order: WorkOrder
    run: WorkflowRun
    approval: PendingApproval | None = None


class DurableOrchestrator:
    """Join durable workflow threads to work-order checkpoints and approval requests."""

    def __init__(
        self,
        engine: WorkflowEngine | None = None,
        work: WorkManager | None = None,
        *,
        procedures: ProcedureStore | None = None,
        approvals: ApprovalStore | None = None,
        context_factory: Callable[[Scope], RunContext] | None = None,
    ) -> None:
        self.engine = engine or make_default_workflow_engine()
        self.work = work or WorkManager()
        self.procedures = procedures or InMemoryProcedureStore()
        self.approvals = approvals or InMemoryApprovalStore()
        self.context_factory = context_factory or (lambda scope: RunContext(scope=scope))

    def submit(self, order: WorkOrder) -> WorkOrder:
        return self.work.submit(order)

    def register(self, procedure: Procedure, scope: Scope) -> None:
        self.procedures.save(procedure, scope)

    async def start(
        self,
        work_id: str,
        scope: Scope,
        *,
        worker: str,
        state: dict[str, Any] | None = None,
        thread_id: str | None = None,
        lease_seconds: int = 300,
    ) -> DurableOrchestrationResult:
        procedure, workflow_scope = self._procedure(work_id, scope)
        lease = self.work.claim(work_id, scope, worker=worker, lease_seconds=lease_seconds)
        self.work.start(lease, scope)
        try:
            run = await self.engine.start(
                procedure,
                state or {},
                self.context_factory(workflow_scope),
                thread_id=thread_id,
            )
        except Exception as exc:
            self.work.fail(lease, scope, error=str(exc), retry=False)
            raise
        return self._apply_run(run, lease=lease, scope=scope, workflow_scope=workflow_scope)

    async def resume(
        self,
        work_id: str,
        scope: Scope,
        *,
        worker: str,
        decision: dict[str, Any] | None = None,
        state: dict[str, Any] | None = None,
        lease_seconds: int = 300,
    ) -> DurableOrchestrationResult:
        order = self.work.get(work_id, scope)
        if order.status != WorkStatus.queued:
            raise ValueError("resolve an interrupted approval before resuming workflow work")
        if order.checkpoint is None:
            raise ValueError("work order has no durable workflow checkpoint")
        if decision is None and order.decisions:
            latest = order.decisions[-1]
            if latest.outcome is DecisionOutcome.accepted:
                decision = {"approved": True}
        thread_id = order.checkpoint.state.get("workflow_thread_id")
        if not isinstance(thread_id, str) or not thread_id:
            raise ValueError("work-order checkpoint does not name a workflow thread")
        procedure, workflow_scope = self._procedure(work_id, scope)
        lease = self.work.claim(work_id, scope, worker=worker, lease_seconds=lease_seconds)
        self.work.start(lease, scope)
        try:
            run = await self.engine.resume(
                thread_id,
                self.context_factory(workflow_scope),
                procedure=procedure,
                decision=decision,
                state=state,
            )
        except Exception as exc:
            self.work.fail(lease, scope, error=str(exc), retry=False)
            raise
        return self._apply_run(run, lease=lease, scope=scope, workflow_scope=workflow_scope)

    def resolve_approval(
        self,
        work_id: str,
        scope: Scope,
        *,
        approved: bool,
        decided_by: str,
    ) -> WorkOrder:
        order = self.work.get(work_id, scope)
        request = order.pending_request
        if request is None or request.kind != "approval":
            raise ValueError("work order is not waiting for workflow approval")
        workflow_approval_id = request.metadata.get("workflow_approval_id")
        if not isinstance(workflow_approval_id, str):
            raise ValueError("approval request is missing workflow approval linkage")
        self.approvals.decide(
            workflow_approval_id,
            scope,
            approved=approved,
            decided_by=decided_by,
        )
        return self.work.decide(
            work_id,
            scope,
            Decision(
                request_id=request.id,
                outcome=DecisionOutcome.accepted if approved else DecisionOutcome.declined,
                decided_by=decided_by,
            ),
        )

    def _procedure(self, work_id: str, scope: Scope) -> tuple[Procedure, Scope]:
        order = self.work.get(work_id, scope)
        if not order.procedure:
            raise ProcedureNotFoundError("work order does not name a procedure")
        procedure = self.procedures.get(order.procedure, scope)
        if procedure is None:
            raise ProcedureNotFoundError(
                f"procedure {order.procedure!r} not found in scope {scope.key!r}"
            )
        return procedure, scope

    def _apply_run(
        self,
        run: WorkflowRun,
        *,
        lease: Lease,
        scope: Scope,
        workflow_scope: Scope,
    ) -> DurableOrchestrationResult:
        if run.status is WorkflowRunStatus.completed:
            return DurableOrchestrationResult(order=self.work.complete(lease, scope), run=run)
        checkpoint = self.work.checkpoint(
            lease,
            scope,
            {"workflow_thread_id": run.thread_id, "state": run.state},
        )
        if run.status is WorkflowRunStatus.failed:
            return DurableOrchestrationResult(
                order=self.work.fail(lease, scope, error="durable workflow failed", retry=False),
                run=run,
            )
        if run.status is WorkflowRunStatus.interrupted:
            if run.interrupt is None:
                raise ValueError("interrupted workflow run is missing interrupt details")
            approval = self.approvals.save(
                PendingApproval(
                    thread_id=run.thread_id,
                    step_id=run.interrupt.step_id,
                    scope=workflow_scope,
                    prompt=run.interrupt.prompt,
                )
            )
            self.work.request_approval(
                lease,
                scope,
                prompt=run.interrupt.prompt,
                metadata={
                    "workflow_approval_id": approval.id,
                    "workflow_thread_id": run.thread_id,
                    "resume_token": checkpoint.value,
                },
            )
            return DurableOrchestrationResult(
                order=self.work.get(lease.work_id, scope), run=run, approval=approval
            )
        return DurableOrchestrationResult(order=self.work.get(lease.work_id, scope), run=run)


# Imports for WorkflowRun / PendingApproval now resolve at the top of the module, so the
# pydantic forward refs above are bound at class-definition time. The explicit rebuild is
# retained as a belt-and-braces no-op in case import order ever shifts.
DurableOrchestrationResult.model_rebuild()
