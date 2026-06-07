"""WorkManager: the small durable-work facade."""

from __future__ import annotations

from collections.abc import Callable, Sequence
from datetime import datetime, timedelta
from typing import Any

from coactra.workflow.ledger.backends.inmemory import InMemoryWorkStore
from coactra.workflow.ledger.domain.artifacts import Artifact
from coactra.workflow.ledger.domain.events import EventEnvelope, utc_now
from coactra.workflow.ledger.domain.models import (
    PAUSED_STATUSES,
    TERMINAL_STATUSES,
    ApprovalRequest,
    Assignment,
    Attempt,
    AttemptStatus,
    Checkpoint,
    Decision,
    DecisionOutcome,
    ElicitationRequest,
    Lease,
    ResumeToken,
    Usage,
    WorkOrder,
    WorkStatus,
)
from coactra.workflow.ledger.domain.plans import ExecutionPlan, ExecutionReceipt
from coactra.workflow.ledger.domain.scope import Scope
from coactra.workflow.ledger.store import AuditSink, ConflictError, WorkStore


class WorkError(RuntimeError):
    """Base exception for invalid work lifecycle operations."""


class WorkNotFoundError(WorkError):
    pass


class InvalidTransitionError(WorkError):
    pass


class LeaseError(WorkError):
    pass


class WorkManager:
    """Tenant-scoped work-order lifecycle with injected persistence and audit sinks."""

    def __init__(
        self,
        store: WorkStore | None = None,
        *,
        audit_sinks: Sequence[AuditSink] = (),
        clock: Callable[[], datetime] = utc_now,
    ) -> None:
        self.store = store or InMemoryWorkStore()
        self.audit_sinks = tuple(audit_sinks)
        self.clock = clock

    def submit(self, order: WorkOrder) -> WorkOrder:
        if order.status != WorkStatus.queued:
            raise InvalidTransitionError("new work order must be queued")
        if order.idempotency_key:
            existing = self.store.find_by_idempotency_key(order.idempotency_key, order.scope)
            if existing is not None:
                return existing
        try:
            return self._save_and_emit(
                order,
                "coactra.workflow.submitted",
                expected_version=None,
                touch_updated_at=False,
            )
        except ConflictError:
            if order.idempotency_key:
                existing = self.store.find_by_idempotency_key(order.idempotency_key, order.scope)
                if existing is not None:
                    return existing
            raise

    def plan(self, *, scope: Scope, title: str, **kwargs: Any) -> ExecutionPlan:
        """Create reviewable intent without persisting or performing work."""
        return ExecutionPlan(scope=scope, title=title, **kwargs)

    def execute(self, plan: ExecutionPlan) -> ExecutionReceipt:
        """Enter an approved plan into the durable queue and return its stable handle."""
        return ExecutionReceipt.from_order(plan, self.submit(plan.to_order()))

    def inspect(self, receipt: ExecutionReceipt) -> WorkOrder:
        """Resolve a receipt to its current durable work-order state."""
        return self.get(receipt.work_order_id, receipt.scope)

    def get(self, work_id: str, scope: Scope) -> WorkOrder:
        order = self.store.get(work_id, scope)
        if order is None:
            raise WorkNotFoundError(f"work order {work_id!r} not found in scope {scope.key!r}")
        return order

    def list(self, scope: Scope, *, status: WorkStatus | None = None) -> list[WorkOrder]:
        return self.store.list(scope, status=status)

    def events(self, work_id: str, scope: Scope) -> list[EventEnvelope]:
        return self.store.events(work_id, scope)

    def claim(self, work_id: str, scope: Scope, *, worker: str, lease_seconds: int = 300) -> Lease:
        if lease_seconds <= 0:
            raise ValueError("lease_seconds must be positive")
        order = self.get(work_id, scope)
        self._ensure_not_terminal(order)
        if order.deadline is not None and order.deadline.expired(at=self.clock()):
            order.status = WorkStatus.failed
            order.error = "deadline exceeded"
            order.lease = None
            order.assignment = None
            self._save_and_emit(order, "coactra.workflow.deadline_exceeded")
            raise InvalidTransitionError("work order deadline has expired")
        if order.status not in {WorkStatus.queued, WorkStatus.claimed}:
            raise InvalidTransitionError(f"cannot claim work in {order.status.value!r} state")
        now = self.clock()
        if order.lease is not None and order.lease.active(at=now):
            if order.lease.worker == worker:
                return order.lease
            raise LeaseError(f"work order is leased by {order.lease.worker!r}")
        lease = Lease(
            work_id=order.id,
            worker=worker,
            heartbeat_at=now,
            expires_at=now + timedelta(seconds=lease_seconds),
        )
        order.status = WorkStatus.claimed
        order.assignment = Assignment(worker=worker, assigned_at=now)
        order.lease = lease
        saved = self._save_and_emit(order, "coactra.workflow.claimed", worker=worker, lease_id=lease.id)
        return saved.lease  # type: ignore[return-value]

    def heartbeat(self, lease: Lease, scope: Scope, *, lease_seconds: int = 300) -> Lease:
        if lease_seconds <= 0:
            raise ValueError("lease_seconds must be positive")
        order = self.get(lease.work_id, scope)
        current = self._require_lease(order, lease, allow_expired=False)
        now = self.clock()
        current.heartbeat_at = now
        current.expires_at = now + timedelta(seconds=lease_seconds)
        saved = self._save_and_emit(order, "coactra.workflow.heartbeat", lease_id=current.id)
        return saved.lease  # type: ignore[return-value]

    def start(self, lease: Lease, scope: Scope) -> WorkOrder:
        order = self.get(lease.work_id, scope)
        self._require_lease(order, lease)
        if order.status == WorkStatus.running:
            return order
        if order.status != WorkStatus.claimed:
            raise InvalidTransitionError(f"cannot start work in {order.status.value!r} state")
        order.status = WorkStatus.running
        order.attempts.append(Attempt(number=len(order.attempts) + 1, worker=lease.worker))
        attempt_number = order.attempts[-1].number
        return self._save_and_emit(order, "coactra.workflow.started", attempt=attempt_number)

    def checkpoint(self, lease: Lease, scope: Scope, state: dict[str, Any]) -> ResumeToken:
        order = self.get(lease.work_id, scope)
        self._require_running(order, lease)
        token = ResumeToken(work_id=order.id)
        order.checkpoint = Checkpoint(token=token, state=state)
        self._save_and_emit(order, "coactra.workflow.checkpointed", resume_token=token.value)
        return token

    def request_input(self, lease: Lease, scope: Scope, *, prompt: str) -> ElicitationRequest:
        request = ElicitationRequest(kind="input", prompt=prompt)
        self._pause(lease, scope, status=WorkStatus.input_required, request=request)
        return request

    def request_auth(self, lease: Lease, scope: Scope, *, prompt: str) -> ElicitationRequest:
        request = ElicitationRequest(kind="auth", prompt=prompt)
        self._pause(lease, scope, status=WorkStatus.auth_required, request=request)
        return request

    def request_approval(
        self, lease: Lease, scope: Scope, *, prompt: str, metadata: dict[str, Any] | None = None
    ) -> ApprovalRequest:
        request = ApprovalRequest(prompt=prompt, metadata=metadata or {})
        self._pause(lease, scope, status=WorkStatus.blocked, request=request)
        return request

    def decide(self, work_id: str, scope: Scope, decision: Decision) -> WorkOrder:
        order = self.get(work_id, scope)
        if order.status not in PAUSED_STATUSES or order.pending_request is None:
            raise InvalidTransitionError("work order is not waiting for a decision")
        if decision.request_id != order.pending_request.id:
            raise InvalidTransitionError("decision does not match pending request")
        order.decisions.append(decision)
        order.pending_request = None
        order.lease = None
        order.assignment = None
        if decision.outcome == DecisionOutcome.accepted:
            order.status = WorkStatus.queued
            event_type = "coactra.workflow.resumed"
        elif decision.outcome == DecisionOutcome.cancelled:
            order.status = WorkStatus.cancelled
            event_type = "coactra.workflow.cancelled"
        else:
            order.status = WorkStatus.failed
            order.error = "request declined"
            event_type = "coactra.workflow.failed"
        return self._save_and_emit(order, event_type, decision=decision.outcome.value)

    def resume(self, work_id: str, scope: Scope, *, token: ResumeToken | None = None) -> WorkOrder:
        order = self.get(work_id, scope)
        if order.status not in PAUSED_STATUSES:
            raise InvalidTransitionError("only paused work can be resumed")
        if order.pending_request is not None:
            raise InvalidTransitionError("resolve the pending request before resuming")
        if token is not None:
            if order.checkpoint is None or order.checkpoint.token != token:
                raise InvalidTransitionError("resume token does not match latest checkpoint")
        order.status = WorkStatus.queued
        order.lease = None
        order.assignment = None
        return self._save_and_emit(order, "coactra.workflow.resumed")

    def record_usage(
        self,
        lease: Lease,
        scope: Scope,
        *,
        input_tokens: int = 0,
        output_tokens: int = 0,
        cost: float = 0.0,
    ) -> WorkOrder:
        order = self.get(lease.work_id, scope)
        self._require_running(order, lease)
        order.usage = Usage(
            input_tokens=order.usage.input_tokens + input_tokens,
            output_tokens=order.usage.output_tokens + output_tokens,
            cost=order.usage.cost + cost,
        )
        if order.budget is not None and not order.budget.allows(
            order.usage, attempts=len(order.attempts)
        ):
            self._finish_attempt(order, AttemptStatus.failed, error="budget exceeded")
            order.status = WorkStatus.failed
            order.error = "budget exceeded"
            order.lease = None
            order.assignment = None
            return self._save_and_emit(order, "coactra.workflow.budget_exceeded")
        return self._save_and_emit(
            order,
            "coactra.workflow.usage_recorded",
            input_tokens=input_tokens,
            output_tokens=output_tokens,
            cost=cost,
        )

    def complete(
        self, lease: Lease, scope: Scope, *, artifacts: Sequence[Artifact] = ()
    ) -> WorkOrder:
        order = self.get(lease.work_id, scope)
        self._require_running(order, lease)
        self._finish_attempt(order, AttemptStatus.completed)
        order.artifacts.extend(artifacts)
        order.status = WorkStatus.completed
        order.lease = None
        order.assignment = None
        return self._save_and_emit(order, "coactra.workflow.completed", artifact_ids=[a.id for a in artifacts])

    def fail(self, lease: Lease, scope: Scope, *, error: str, retry: bool = True) -> WorkOrder:
        order = self.get(lease.work_id, scope)
        self._require_running(order, lease)
        self._finish_attempt(order, AttemptStatus.failed, error=error)
        order.error = error
        order.lease = None
        order.assignment = None
        if retry and len(order.attempts) < self._attempts_allowed(order):
            order.status = WorkStatus.queued
            event_type = "coactra.workflow.retry_scheduled"
        else:
            order.status = WorkStatus.failed
            event_type = "coactra.workflow.failed"
        return self._save_and_emit(order, event_type, error=error)

    def cancel(self, work_id: str, scope: Scope, *, reason: str = "") -> WorkOrder:
        order = self.get(work_id, scope)
        self._ensure_not_terminal(order)
        if order.status == WorkStatus.running:
            self._finish_attempt(order, AttemptStatus.interrupted, error=reason or "cancelled")
        order.status = WorkStatus.cancelled
        order.error = reason or None
        order.lease = None
        order.assignment = None
        order.pending_request = None
        return self._save_and_emit(order, "coactra.workflow.cancelled", reason=reason)

    def reap_stale(self, scope: Scope, *, retry: bool = True) -> list[WorkOrder]:
        """Watchdog pass for expired leases and deadlines in one scope.

        Expired deadlines fail permanently. Expired claimed/running leases are
        requeued when retry budget remains, otherwise failed. This lets workers
        recover work abandoned by crashed processes without bypassing the normal
        attempts, lease, and audit-event model.
        """
        now = self.clock()
        reaped: list[WorkOrder] = []
        for order in self.list(scope):
            if order.status in TERMINAL_STATUSES:
                continue

            event_type: str | None = None
            event_data: dict[str, Any] = {}

            if order.deadline is not None and order.deadline.expired(at=now):
                if order.status == WorkStatus.running and _has_running_attempt(order):
                    self._finish_attempt(order, AttemptStatus.failed, error="deadline exceeded")
                order.status = WorkStatus.failed
                order.error = "deadline exceeded"
                order.lease = None
                order.assignment = None
                event_type = "coactra.workflow.deadline_exceeded"
            elif (
                order.status in {WorkStatus.claimed, WorkStatus.running}
                and order.lease is not None
                and not order.lease.active(at=now)
            ):
                worker = order.lease.worker
                if order.status == WorkStatus.running and _has_running_attempt(order):
                    self._finish_attempt(order, AttemptStatus.interrupted, error="lease expired")
                order.lease = None
                order.assignment = None
                order.error = "lease expired"
                if retry and len(order.attempts) < self._attempts_allowed(order):
                    order.status = WorkStatus.queued
                    event_type = "coactra.workflow.stale_requeued"
                else:
                    order.status = WorkStatus.failed
                    event_type = "coactra.workflow.stale_failed"
                event_data = {"worker": worker}

            if event_type is None:
                continue
            saved = self._save_and_emit(order, event_type, **event_data)
            reaped.append(saved)
        return reaped

    def _pause(
        self,
        lease: Lease,
        scope: Scope,
        *,
        status: WorkStatus,
        request: ApprovalRequest | ElicitationRequest,
    ) -> WorkOrder:
        order = self.get(lease.work_id, scope)
        self._require_running(order, lease)
        self._finish_attempt(order, AttemptStatus.interrupted)
        order.status = status
        order.pending_request = request
        order.lease = None
        order.assignment = None
        return self._save_and_emit(order, f"coactra.workflow.{status.value}", request_id=request.id)

    def _save_and_emit(
        self,
        order: WorkOrder,
        event_type: str,
        *,
        expected_version: int | None = None,
        touch_updated_at: bool = True,
        **data: Any,
    ) -> WorkOrder:
        if touch_updated_at:
            order.updated_at = self.clock()
        if expected_version is None:
            expected_version = order.version
        event = self._event_for(order, event_type, **data)
        save_with_event = getattr(self.store, "save_with_event", None)
        if callable(save_with_event):
            saved = save_with_event(order, event, expected_version=expected_version)
        else:
            saved = self.store.save(order, expected_version=expected_version)
            self.store.append_event(event)
        for sink in self.audit_sinks:
            sink.emit(event)
        return saved

    def _event_for(self, order: WorkOrder, event_type: str, **data: Any) -> EventEnvelope:
        context = order.audit_context.event_data()
        return EventEnvelope(
            type=event_type,
            subject=order.id,
            tenant_id=order.scope.tenant_id,
            data={
                "namespace": order.scope.namespace,
                "status": order.status.value,
                "parent_work_order_id": order.parent_id,
                "correlation_id": order.correlation_id,
                **context,
                **data,
            },
        )

    def _ensure_not_terminal(self, order: WorkOrder) -> None:
        if order.status in TERMINAL_STATUSES:
            raise InvalidTransitionError(f"work order is already {order.status.value}")

    def _require_lease(self, order: WorkOrder, lease: Lease, *, allow_expired: bool = False) -> Lease:
        current = order.lease
        if current is None or current.id != lease.id or current.worker != lease.worker:
            raise LeaseError("lease does not own this work order")
        if not allow_expired and not current.active(at=self.clock()):
            raise LeaseError("lease has expired")
        return current

    def _require_running(self, order: WorkOrder, lease: Lease) -> None:
        self._require_lease(order, lease)
        if order.status != WorkStatus.running:
            raise InvalidTransitionError(f"work order is not running: {order.status.value!r}")

    def _finish_attempt(
        self, order: WorkOrder, status: AttemptStatus, *, error: str | None = None
    ) -> None:
        if not order.attempts or order.attempts[-1].status != AttemptStatus.running:
            raise InvalidTransitionError("work order has no running attempt")
        attempt = order.attempts[-1]
        attempt.status = status
        attempt.error = error
        attempt.finished_at = self.clock()

    def _attempts_allowed(self, order: WorkOrder) -> int:
        budget_attempts = (
            order.budget.max_attempts
            if order.budget is not None and order.budget.max_attempts
            else 2**31
        )
        return min(order.retry_policy.max_attempts, budget_attempts)


def _has_running_attempt(order: WorkOrder) -> bool:
    return bool(order.attempts and order.attempts[-1].status == AttemptStatus.running)
