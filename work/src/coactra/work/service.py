"""WorkManager: the small durable-work facade."""

from __future__ import annotations

from collections.abc import Callable, Sequence
from datetime import datetime, timedelta
from typing import Any

from coactra.work.backends.inmemory import InMemoryWorkStore
from coactra.work.domain.artifacts import Artifact
from coactra.work.domain.events import EventEnvelope, utc_now
from coactra.work.domain.models import (
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
from coactra.work.domain.scope import Scope
from coactra.work.store import AuditSink, WorkStore


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
        saved = self.store.save(order)
        self._emit(saved, "coactra.work.submitted")
        return saved

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
            saved = self._save(order)
            self._emit(saved, "coactra.work.deadline_exceeded")
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
        saved = self._save(order)
        self._emit(saved, "coactra.work.claimed", worker=worker, lease_id=lease.id)
        return saved.lease  # type: ignore[return-value]

    def heartbeat(self, lease: Lease, scope: Scope, *, lease_seconds: int = 300) -> Lease:
        if lease_seconds <= 0:
            raise ValueError("lease_seconds must be positive")
        order = self.get(lease.work_id, scope)
        current = self._require_lease(order, lease, allow_expired=False)
        now = self.clock()
        current.heartbeat_at = now
        current.expires_at = now + timedelta(seconds=lease_seconds)
        saved = self._save(order)
        self._emit(saved, "coactra.work.heartbeat", lease_id=current.id)
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
        saved = self._save(order)
        self._emit(saved, "coactra.work.started", attempt=saved.attempts[-1].number)
        return saved

    def checkpoint(self, lease: Lease, scope: Scope, state: dict[str, Any]) -> ResumeToken:
        order = self.get(lease.work_id, scope)
        self._require_running(order, lease)
        token = ResumeToken(work_id=order.id)
        order.checkpoint = Checkpoint(token=token, state=state)
        saved = self._save(order)
        self._emit(saved, "coactra.work.checkpointed", resume_token=token.value)
        return token

    def request_input(self, lease: Lease, scope: Scope, *, prompt: str) -> ElicitationRequest:
        request = ElicitationRequest(kind="input", prompt=prompt)
        self._pause(lease, scope, status=WorkStatus.input_required, request=request)
        return request

    def request_auth(self, lease: Lease, scope: Scope, *, prompt: str) -> ElicitationRequest:
        request = ElicitationRequest(kind="auth", prompt=prompt)
        self._pause(lease, scope, status=WorkStatus.auth_required, request=request)
        return request

    def request_approval(self, lease: Lease, scope: Scope, *, prompt: str) -> ApprovalRequest:
        request = ApprovalRequest(prompt=prompt)
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
            event_type = "coactra.work.resumed"
        elif decision.outcome == DecisionOutcome.cancelled:
            order.status = WorkStatus.cancelled
            event_type = "coactra.work.cancelled"
        else:
            order.status = WorkStatus.failed
            order.error = "request declined"
            event_type = "coactra.work.failed"
        saved = self._save(order)
        self._emit(saved, event_type, decision=decision.outcome.value)
        return saved

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
        saved = self._save(order)
        self._emit(saved, "coactra.work.resumed")
        return saved

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
            saved = self._save(order)
            self._emit(saved, "coactra.work.budget_exceeded")
            return saved
        saved = self._save(order)
        self._emit(
            saved,
            "coactra.work.usage_recorded",
            input_tokens=input_tokens,
            output_tokens=output_tokens,
            cost=cost,
        )
        return saved

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
        saved = self._save(order)
        self._emit(saved, "coactra.work.completed", artifact_ids=[a.id for a in artifacts])
        return saved

    def fail(self, lease: Lease, scope: Scope, *, error: str, retry: bool = True) -> WorkOrder:
        order = self.get(lease.work_id, scope)
        self._require_running(order, lease)
        self._finish_attempt(order, AttemptStatus.failed, error=error)
        order.error = error
        order.lease = None
        order.assignment = None
        attempts_allowed = min(
            order.retry_policy.max_attempts,
            order.budget.max_attempts if order.budget and order.budget.max_attempts else 2**31,
        )
        if retry and len(order.attempts) < attempts_allowed:
            order.status = WorkStatus.queued
            event_type = "coactra.work.retry_scheduled"
        else:
            order.status = WorkStatus.failed
            event_type = "coactra.work.failed"
        saved = self._save(order)
        self._emit(saved, event_type, error=error)
        return saved

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
        saved = self._save(order)
        self._emit(saved, "coactra.work.cancelled", reason=reason)
        return saved

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
        saved = self._save(order)
        self._emit(saved, f"coactra.work.{status.value}", request_id=request.id)
        return saved

    def _save(self, order: WorkOrder) -> WorkOrder:
        order.updated_at = self.clock()
        return self.store.save(order, expected_version=order.version)

    def _emit(self, order: WorkOrder, event_type: str, **data: Any) -> None:
        event = EventEnvelope(
            type=event_type,
            subject=order.id,
            tenant_id=order.scope.tenant_id,
            data={"namespace": order.scope.namespace, "status": order.status.value, **data},
        )
        self.store.append_event(event)
        for sink in self.audit_sinks:
            sink.emit(event)

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
