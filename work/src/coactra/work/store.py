"""Storage and audit ports for durable work orders."""

from __future__ import annotations

from typing import Protocol, runtime_checkable

from coactra.work.domain.artifacts import Artifact, ArtifactRef
from coactra.work.domain.events import EventEnvelope
from coactra.work.domain.models import WorkOrder, WorkStatus
from coactra.work.domain.scope import Scope


class ConflictError(RuntimeError):
    """Raised when optimistic concurrency detects a stale write."""


@runtime_checkable
class WorkStore(Protocol):
    def save(self, order: WorkOrder, *, expected_version: int | None = None) -> WorkOrder:
        """Insert or update an order and return a detached copy."""
        ...

    def get(self, work_id: str, scope: Scope) -> WorkOrder | None:
        """Fetch one order within scope."""
        ...

    def find_by_idempotency_key(self, key: str, scope: Scope) -> WorkOrder | None:
        """Fetch a previously submitted order within scope."""
        ...

    def list(self, scope: Scope, *, status: WorkStatus | None = None) -> list[WorkOrder]:
        """List orders within scope, optionally filtered by status."""
        ...

    def append_event(self, event: EventEnvelope) -> None:
        """Persist one audit event."""
        ...

    def events(self, work_id: str, scope: Scope) -> list[EventEnvelope]:
        """Read events for one order within scope."""
        ...


@runtime_checkable
class AuditSink(Protocol):
    def emit(self, event: EventEnvelope) -> None:
        """Publish one event to an external audit or telemetry system."""
        ...


@runtime_checkable
class ArtifactStore(Protocol):
    def put(self, artifact: "Artifact", scope: Scope) -> "ArtifactRef":
        """Persist one artifact and return a backend-neutral reference."""
        ...

    def get(self, reference: "ArtifactRef", scope: Scope) -> "Artifact":
        """Read one artifact within scope."""
        ...
