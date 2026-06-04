"""Reusable contract probes for work-store adapters."""

from __future__ import annotations

import uuid

from pydantic import BaseModel

from coactra.orchestration.work.domain.events import EventEnvelope
from coactra.orchestration.work.domain.models import WorkOrder
from coactra.orchestration.work.domain.scope import Scope
from coactra.orchestration.work.store import WorkStore


class WorkStoreReport(BaseModel):
    backend: str
    work_id: str
    events: int


def check_work_store_contract(store: WorkStore) -> WorkStoreReport:
    """Exercise save/get/list/idempotency/events with an isolated probe scope."""

    scope = Scope(tenant_id=f"contract-{uuid.uuid4().hex}")
    order = WorkOrder(
        scope=scope,
        title="contract probe",
        idempotency_key=f"probe-{uuid.uuid4().hex}",
    )
    saved = store.save(order)
    if store.get(saved.id, scope) is None:
        raise AssertionError("work store failed get() after save()")
    if store.find_by_idempotency_key(saved.idempotency_key or "", scope) is None:
        raise AssertionError("work store failed idempotency-key lookup")
    if not store.list(scope):
        raise AssertionError("work store failed list() after save()")
    event = EventEnvelope(
        type="coactra.work.contract_probe",
        subject=saved.id,
        tenant_id=scope.tenant_id,
        data={"namespace": scope.namespace},
    )
    store.append_event(event)
    events = store.events(saved.id, scope)
    if not events:
        raise AssertionError("work store failed events() after append_event()")
    return WorkStoreReport(
        backend=type(store).__name__,
        work_id=saved.id,
        events=len(events),
    )
