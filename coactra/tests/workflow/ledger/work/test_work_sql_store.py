from __future__ import annotations

import pytest

from coactra import Scope as WorkScope
from coactra.workflow.ledger import (
    ConflictError,
    Decision,
    DecisionOutcome,
    EventEnvelope,
    ExecutionPlan,
    LeaseError,
    SqlWorkStore,
    WorkManager,
    WorkOrder,
    WorkStatus,
)


def make_store(tmp_path):
    return SqlWorkStore.from_url(f"sqlite:///{tmp_path / 'work.db'}")


def test_sql_store_create_and_load_work_order(tmp_path):
    store = make_store(tmp_path)
    scope = WorkScope(tenant_id="acme", namespace="agent-build")
    order = store.save(WorkOrder(scope=scope, title="build docs"))

    loaded = store.get(order.id, scope)

    assert loaded is not None
    assert loaded.id == order.id
    assert loaded.title == "build docs"
    assert loaded.version == 1
    assert loaded.status is WorkStatus.queued


def test_sql_store_updates_status_through_work_manager(tmp_path):
    manager = WorkManager(store=make_store(tmp_path))
    scope = WorkScope(tenant_id="acme", namespace="agent-build")
    order = manager.submit(WorkOrder(scope=scope, title="build docs"))
    lease = manager.claim(order.id, scope, worker="worker-1")
    running = manager.start(lease, scope)

    assert running.status is WorkStatus.running
    assert manager.get(order.id, scope).status is WorkStatus.running


def test_sql_store_claim_lease_persists_and_blocks_other_worker(tmp_path):
    manager = WorkManager(store=make_store(tmp_path))
    scope = WorkScope(tenant_id="acme", namespace="agent-build")
    order = manager.submit(WorkOrder(scope=scope, title="build docs"))
    lease = manager.claim(order.id, scope, worker="worker-1", lease_seconds=60)

    with pytest.raises(LeaseError):
        manager.claim(order.id, scope, worker="worker-2", lease_seconds=60)

    loaded = manager.get(order.id, scope)
    assert loaded.lease is not None
    assert loaded.lease.id == lease.id
    assert loaded.lease.worker == "worker-1"


def test_sql_store_two_worker_claim_race_allows_only_one_winner(tmp_path):
    import threading

    store = make_store(tmp_path)
    manager = WorkManager(store=store)
    scope = WorkScope(tenant_id="acme", namespace="agent-build")
    order = manager.submit(WorkOrder(scope=scope, title="build docs"))
    barrier = threading.Barrier(2)
    results: list[tuple[str, str]] = []
    lock = threading.Lock()

    def claim(worker: str) -> None:
        local_manager = WorkManager(store=store)
        barrier.wait()
        try:
            lease = local_manager.claim(order.id, scope, worker=worker, lease_seconds=60)
            outcome = ("won", lease.worker)
        except (ConflictError, LeaseError) as exc:
            outcome = ("lost", type(exc).__name__)
        with lock:
            results.append(outcome)

    threads = [
        threading.Thread(target=claim, args=("worker-1",)),
        threading.Thread(target=claim, args=("worker-2",)),
    ]
    for thread in threads:
        thread.start()
    for thread in threads:
        thread.join()

    winners = [value for status, value in results if status == "won"]
    assert len(winners) == 1
    persisted = manager.get(order.id, scope)
    assert persisted.lease is not None
    assert persisted.lease.worker == winners[0]


def test_sql_store_optimistic_version_conflict_blocks_stale_save(tmp_path):
    store = make_store(tmp_path)
    scope = WorkScope(tenant_id="acme", namespace="agent-build")
    order = store.save(WorkOrder(scope=scope, title="build docs"))
    first = store.get(order.id, scope)
    stale = store.get(order.id, scope)
    assert first is not None and stale is not None

    first.status = WorkStatus.claimed
    store.save(first, expected_version=first.version)
    stale.status = WorkStatus.running

    with pytest.raises(ConflictError):
        store.save(stale, expected_version=stale.version)

    assert store.get(order.id, scope).status is WorkStatus.claimed


def test_sql_store_checkpoint_save_and_load(tmp_path):
    manager = WorkManager(store=make_store(tmp_path))
    scope = WorkScope(tenant_id="acme", namespace="agent-build")
    order = manager.submit(WorkOrder(scope=scope, title="build docs"))
    lease = manager.claim(order.id, scope, worker="worker-1")
    manager.start(lease, scope)
    token = manager.checkpoint(lease, scope, {"step": "compile", "ok": True})

    loaded = manager.get(order.id, scope)

    assert loaded.checkpoint is not None
    assert loaded.checkpoint.token == token
    assert loaded.checkpoint.state == {"step": "compile", "ok": True}


def test_sql_store_approval_state_save_and_load(tmp_path):
    manager = WorkManager(store=make_store(tmp_path))
    scope = WorkScope(tenant_id="acme", namespace="agent-build")
    order = manager.submit(WorkOrder(scope=scope, title="build docs"))
    lease = manager.claim(order.id, scope, worker="worker-1")
    manager.start(lease, scope)
    request = manager.request_approval(lease, scope, prompt="Deploy?")

    loaded = manager.get(order.id, scope)

    assert loaded.status is WorkStatus.blocked
    assert loaded.pending_request is not None
    assert loaded.pending_request.id == request.id
    assert loaded.pending_request.prompt == "Deploy?"


def test_sql_store_retry_attempt_persistence(tmp_path):
    manager = WorkManager(store=make_store(tmp_path))
    scope = WorkScope(tenant_id="acme", namespace="agent-build")
    order = manager.submit(WorkOrder(scope=scope, title="build docs"))
    first_lease = manager.claim(order.id, scope, worker="worker-1")
    manager.start(first_lease, scope)
    failed = manager.fail(first_lease, scope, error="network", retry=True)

    assert failed.status is WorkStatus.queued
    assert failed.attempts[0].error == "network"

    second_lease = manager.claim(order.id, scope, worker="worker-2")
    retried = manager.start(second_lease, scope)

    assert len(retried.attempts) == 2
    assert retried.attempts[0].error == "network"
    assert retried.attempts[1].worker == "worker-2"


def test_sql_store_sqlite_file_reopen_persists_orders_and_events(tmp_path):
    url = f"sqlite:///{tmp_path / 'work.db'}"
    scope = WorkScope(tenant_id="acme", namespace="agent-build")
    first_store = SqlWorkStore.from_url(url)
    manager = WorkManager(store=first_store)
    order = manager.submit(WorkOrder(scope=scope, title="build docs"))
    lease = manager.claim(order.id, scope, worker="worker-1")
    manager.start(lease, scope)

    reopened = SqlWorkStore.from_url(url)
    loaded = reopened.get(order.id, scope)
    events = reopened.events(order.id, scope)

    assert loaded is not None
    assert loaded.status is WorkStatus.running
    assert [event.type for event in events] == [
        "coactra.workflow.submitted",
        "coactra.workflow.claimed",
        "coactra.workflow.started",
    ]


def test_sql_store_idempotency_key_is_scoped(tmp_path):
    store = make_store(tmp_path)
    manager = WorkManager(store=store)
    acme = WorkScope(tenant_id="acme", namespace="agent-build")
    globex = WorkScope(tenant_id="globex", namespace="agent-build")
    first = manager.submit(WorkOrder(scope=acme, title="build docs", idempotency_key="same"))
    second = manager.submit(WorkOrder(scope=acme, title="duplicate", idempotency_key="same"))
    third = manager.submit(WorkOrder(scope=globex, title="other tenant", idempotency_key="same"))

    assert second.id == first.id
    assert third.id != first.id


def test_sql_store_idempotent_submit_race_returns_single_order(tmp_path):
    import threading

    store = make_store(tmp_path)
    scope = WorkScope(tenant_id="acme", namespace="agent-build")
    barrier = threading.Barrier(2)
    results: list[str] = []
    errors: list[BaseException] = []
    lock = threading.Lock()

    def submit(title: str) -> None:
        try:
            manager = WorkManager(store=store)
            barrier.wait()
            submitted = manager.submit(WorkOrder(scope=scope, title=title, idempotency_key="same"))
            with lock:
                results.append(submitted.id)
        except BaseException as exc:  # noqa: BLE001 - re-raised in the main test thread.
            with lock:
                errors.append(exc)

    threads = [
        threading.Thread(target=submit, args=("first",)),
        threading.Thread(target=submit, args=("second",)),
    ]
    for thread in threads:
        thread.start()
    for thread in threads:
        thread.join()

    manager = WorkManager(store=store)
    assert errors == []
    assert len(results) == 2
    assert len(set(results)) == 1
    assert len(manager.list(scope)) == 1


def test_sql_store_save_with_event_persists_order_and_event_atomically(tmp_path):
    store = make_store(tmp_path)
    scope = WorkScope(tenant_id="acme", namespace="agent-build")
    order = WorkOrder(scope=scope, title="build docs")
    event = EventEnvelope(
        type="coactra.workflow.submitted",
        subject=order.id,
        tenant_id=scope.tenant_id,
        data={"namespace": scope.namespace, "status": WorkStatus.queued.value},
    )

    saved = store.save_with_event(order, event)

    assert store.get(saved.id, scope) is not None
    assert store.events(saved.id, scope) == [event]


def test_sql_store_compatible_with_execution_plan_receipt_flow(tmp_path):
    manager = WorkManager(store=make_store(tmp_path))
    scope = WorkScope(tenant_id="acme", namespace="agent-build")
    plan = ExecutionPlan(scope=scope, title="ship release")
    receipt = manager.execute(plan)

    loaded = manager.inspect(receipt)

    assert loaded.id == receipt.work_order_id
    assert loaded.title == "ship release"
    assert loaded.status is WorkStatus.queued


def test_sql_store_decision_persistence_after_approval(tmp_path):
    manager = WorkManager(store=make_store(tmp_path))
    scope = WorkScope(tenant_id="acme", namespace="agent-build")
    order = manager.submit(WorkOrder(scope=scope, title="deploy"))
    lease = manager.claim(order.id, scope, worker="worker-1")
    manager.start(lease, scope)
    request = manager.request_approval(lease, scope, prompt="Deploy?")
    decided = manager.decide(
        order.id,
        scope,
        Decision(
            request_id=request.id,
            outcome=DecisionOutcome.accepted,
            decided_by="human:lead",
        ),
    )

    loaded = manager.get(order.id, scope)

    assert decided.status is WorkStatus.queued
    assert loaded.decisions[0].decided_by == "human:lead"
    assert loaded.pending_request is None
