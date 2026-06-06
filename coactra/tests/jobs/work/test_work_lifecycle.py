from datetime import datetime, timedelta, timezone

import pytest

from coactra.jobs import Scope, WorkManager, WorkOrder
from coactra.jobs.work import (
    Artifact,
    ArtifactPart,
    Budget,
    CapabilityDescriptor,
    CapabilityRequirement,
    CapabilitySet,
    Decision,
    Deadline,
    DecisionOutcome,
    InMemoryWorkStore,
    InvalidTransitionError,
    LeaseError,
    RetryPolicy,
    WorkNotFoundError,
    WorkStatus,
)


class AuditRecorder:
    def __init__(self) -> None:
        self.events = []

    def emit(self, event) -> None:
        self.events.append(event)


class Clock:
    def __init__(self) -> None:
        self.now = datetime(2026, 1, 1, tzinfo=timezone.utc)

    def __call__(self):
        return self.now

    def advance(self, *, seconds: int) -> None:
        self.now += timedelta(seconds=seconds)


def test_submit_is_idempotent_within_scope_only():
    manager = WorkManager()
    acme = Scope(tenant_id="acme")
    globex = Scope(tenant_id="globex")

    first = manager.submit(WorkOrder(scope=acme, title="index docs", idempotency_key="evt-1"))
    duplicate = manager.submit(WorkOrder(scope=acme, title="different", idempotency_key="evt-1"))
    other_tenant = manager.submit(WorkOrder(scope=globex, title="index docs", idempotency_key="evt-1"))

    assert duplicate.id == first.id
    assert other_tenant.id != first.id


def test_full_pause_resume_completion_lifecycle_with_artifact_and_events():
    audit = AuditRecorder()
    manager = WorkManager(audit_sinks=[audit])
    scope = Scope(tenant_id="acme", namespace="support")
    order = manager.submit(WorkOrder(scope=scope, title="prepare report"))

    lease = manager.claim(order.id, scope, worker="agent:analyst")
    manager.start(lease, scope)
    token = manager.checkpoint(lease, scope, {"page": 3})
    request = manager.request_approval(lease, scope, prompt="Publish the report?")

    waiting = manager.get(order.id, scope)
    assert waiting.status == WorkStatus.blocked
    assert waiting.checkpoint.token == token
    assert waiting.lease is None

    manager.decide(
        order.id,
        scope,
        Decision(
            request_id=request.id,
            outcome=DecisionOutcome.accepted,
            decided_by="human:owner",
        ),
    )
    second_lease = manager.claim(order.id, scope, worker="agent:analyst")
    manager.start(second_lease, scope)
    artifact = Artifact(name="report", parts=[ArtifactPart(kind="text", text="done")])
    completed = manager.complete(second_lease, scope, artifacts=[artifact])

    assert completed.status == WorkStatus.completed
    assert completed.artifacts == [artifact]
    assert [attempt.status for attempt in completed.attempts] == ["interrupted", "completed"]
    assert audit.events == manager.events(order.id, scope)
    assert audit.events[-1].type == "coactra.jobs.completed"


def test_failed_work_requeues_until_retry_policy_is_exhausted():
    manager = WorkManager()
    scope = Scope(tenant_id="acme")
    order = manager.submit(
        WorkOrder(scope=scope, title="unstable operation", retry_policy=RetryPolicy(max_attempts=2))
    )

    first = manager.claim(order.id, scope, worker="agent:worker")
    manager.start(first, scope)
    assert manager.fail(first, scope, error="temporary").status == WorkStatus.queued

    second = manager.claim(order.id, scope, worker="agent:worker")
    manager.start(second, scope)
    failed = manager.fail(second, scope, error="still broken")
    assert failed.status == WorkStatus.failed
    assert [event.type for event in manager.events(order.id, scope)][-2:] == [
        "coactra.jobs.started",
        "coactra.jobs.failed",
    ]


def test_lease_expiry_allows_reclaim_but_rejects_old_worker():
    clock = Clock()
    manager = WorkManager(clock=clock)
    scope = Scope(tenant_id="acme")
    order = manager.submit(WorkOrder(scope=scope, title="leased operation"))
    old = manager.claim(order.id, scope, worker="agent:one", lease_seconds=5)

    clock.advance(seconds=6)
    current = manager.claim(order.id, scope, worker="agent:two")
    assert current.worker == "agent:two"
    with pytest.raises(LeaseError):
        manager.heartbeat(old, scope)


def test_scope_isolation_applies_to_orders_and_events():
    store = InMemoryWorkStore()
    manager = WorkManager(store)
    acme = Scope(tenant_id="acme", namespace="private")
    public = Scope(tenant_id="acme", namespace="public")
    order = manager.submit(WorkOrder(scope=acme, title="secret"))

    with pytest.raises(WorkNotFoundError):
        manager.get(order.id, public)
    assert manager.events(order.id, public) == []


def test_capabilities_can_match_required_features():
    capabilities = CapabilitySet(items=[CapabilityDescriptor(name="browser")])
    assert capabilities.satisfies([CapabilityRequirement(name="browser")])
    assert not capabilities.satisfies([CapabilityRequirement(name="gpu")])


def test_expired_deadline_rejects_claim_and_marks_work_failed():
    clock = Clock()
    manager = WorkManager(clock=clock)
    scope = Scope(tenant_id="acme")
    order = manager.submit(
        WorkOrder(scope=scope, title="time boxed", deadline=Deadline(due_at=clock.now))
    )

    with pytest.raises(InvalidTransitionError, match="deadline"):
        manager.claim(order.id, scope, worker="agent:worker")

    failed = manager.get(order.id, scope)
    assert failed.status == WorkStatus.failed
    assert failed.error == "deadline exceeded"
    assert manager.events(order.id, scope)[-1].type == "coactra.jobs.deadline_exceeded"


def test_usage_budget_stops_running_work_and_releases_lease():
    manager = WorkManager()
    scope = Scope(tenant_id="acme")
    order = manager.submit(
        WorkOrder(scope=scope, title="bounded", budget=Budget(max_tokens=3))
    )
    lease = manager.claim(order.id, scope, worker="agent:worker")
    manager.start(lease, scope)

    failed = manager.record_usage(lease, scope, input_tokens=2, output_tokens=2)

    assert failed.status == WorkStatus.failed
    assert failed.error == "budget exceeded"
    assert failed.usage.total_tokens == 4
    assert failed.lease is None
    assert failed.assignment is None
    assert failed.attempts[-1].status == "failed"
    assert manager.events(order.id, scope)[-1].type == "coactra.jobs.budget_exceeded"
