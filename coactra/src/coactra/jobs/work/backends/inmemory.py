"""Tenant-isolated in-memory backend for local use and tests."""

from __future__ import annotations

from coactra.jobs.work.domain.events import EventEnvelope
from coactra.jobs.work.domain.models import WorkOrder, WorkStatus
from coactra.jobs.work.domain.scope import Scope
from coactra.jobs.work.store import ConflictError


class InMemoryWorkStore:
    """Offline default with optimistic concurrency and detached return values."""

    def __init__(self) -> None:
        self._orders: dict[str, WorkOrder] = {}
        self._events: list[EventEnvelope] = []

    def save(self, order: WorkOrder, *, expected_version: int | None = None) -> WorkOrder:
        current = self._orders.get(order.id)
        if current is not None and current.scope != order.scope:
            raise ConflictError("work id already belongs to another scope")
        if expected_version is not None:
            actual = current.version if current is not None else 0
            if actual != expected_version:
                raise ConflictError(
                    f"stale work order {order.id!r}: expected version {expected_version}, got {actual}"
                )
        stored = order.model_copy(deep=True, update={"version": (current.version + 1) if current else 1})
        self._orders[stored.id] = stored
        return stored.model_copy(deep=True)

    def save_with_event(
        self,
        order: WorkOrder,
        event: EventEnvelope,
        *,
        expected_version: int | None = None,
    ) -> WorkOrder:
        saved = self.save(order, expected_version=expected_version)
        self.append_event(event)
        return saved

    def get(self, work_id: str, scope: Scope) -> WorkOrder | None:
        order = self._orders.get(work_id)
        if order is None or order.scope != scope:
            return None
        return order.model_copy(deep=True)

    def find_by_idempotency_key(self, key: str, scope: Scope) -> WorkOrder | None:
        for order in self._orders.values():
            if order.scope == scope and order.idempotency_key == key:
                return order.model_copy(deep=True)
        return None

    def list(self, scope: Scope, *, status: WorkStatus | None = None) -> list[WorkOrder]:
        return [
            order.model_copy(deep=True)
            for order in self._orders.values()
            if order.scope == scope and (status is None or order.status == status)
        ]

    def append_event(self, event: EventEnvelope) -> None:
        self._events.append(event.model_copy(deep=True))

    def events(self, work_id: str, scope: Scope) -> list[EventEnvelope]:
        return [
            event.model_copy(deep=True)
            for event in self._events
            if event.subject == work_id
            and event.tenant_id == scope.tenant_id
            and event.data.get("namespace") == scope.namespace
        ]
