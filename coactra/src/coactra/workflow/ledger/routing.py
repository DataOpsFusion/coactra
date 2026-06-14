"""Tenant-routed work stores for hard physical silo isolation."""

from __future__ import annotations

from coactra._routing import TenantRouter
from coactra.workflow.ledger.domain.events import EventEnvelope
from coactra.workflow.ledger.domain.models import WorkOrder, WorkStatus
from coactra.workflow.ledger.domain.scope import Scope
from coactra.workflow.ledger.store import WorkStore


class TenantWorkStoreRouter(TenantRouter[WorkStore]):
    def save(self, order: WorkOrder, *, expected_version: int | None = None) -> WorkOrder:
        return self.for_tenant(order.scope.tenant_id).save(order, expected_version=expected_version)

    def get(self, work_id: str, scope: Scope) -> WorkOrder | None:
        return self.for_tenant(scope.tenant_id).get(work_id, scope)

    def find_by_idempotency_key(self, key: str, scope: Scope) -> WorkOrder | None:
        return self.for_tenant(scope.tenant_id).find_by_idempotency_key(key, scope)

    def list(self, scope: Scope, *, status: WorkStatus | None = None) -> list[WorkOrder]:
        return self.for_tenant(scope.tenant_id).list(scope, status=status)

    def save_with_event(
        self,
        order: WorkOrder,
        event: EventEnvelope,
        *,
        expected_version: int | None = None,
    ) -> WorkOrder:
        store = self.for_tenant(order.scope.tenant_id)
        save_with_event = getattr(store, "save_with_event", None)
        if callable(save_with_event):
            return save_with_event(order, event, expected_version=expected_version)
        saved = store.save(order, expected_version=expected_version)
        store.append_event(event)
        return saved

    def append_event(self, event: EventEnvelope) -> None:
        self.for_tenant(event.tenant_id).append_event(event)

    def events(self, work_id: str, scope: Scope) -> list[EventEnvelope]:
        return self.for_tenant(scope.tenant_id).events(work_id, scope)
