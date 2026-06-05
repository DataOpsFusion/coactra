"""Durable approval records for interrupt-and-resume workflow engines."""
from __future__ import annotations

import uuid
from datetime import datetime, timezone
from enum import Enum
from typing import Protocol, runtime_checkable

from pydantic import BaseModel, Field

from coactra.jobs.workflow.domain.scope import Scope


def _utc_now() -> datetime:
    return datetime.now(timezone.utc)


class ApprovalStatus(str, Enum):
    pending = "pending"
    approved = "approved"
    rejected = "rejected"


class PendingApproval(BaseModel):
    id: str = Field(default_factory=lambda: uuid.uuid4().hex)
    thread_id: str = Field(min_length=1)
    step_id: str = Field(min_length=1)
    scope: Scope
    prompt: str = Field(min_length=1)
    status: ApprovalStatus = ApprovalStatus.pending
    decided_by: str | None = None
    requested_at: datetime = Field(default_factory=_utc_now)
    decided_at: datetime | None = None


@runtime_checkable
class ApprovalStore(Protocol):
    def save(self, approval: PendingApproval) -> PendingApproval: ...
    def get(self, approval_id: str, scope: Scope) -> PendingApproval | None: ...
    def pending(self, scope: Scope) -> list[PendingApproval]: ...
    def decide(
        self, approval_id: str, scope: Scope, *, approved: bool, decided_by: str
    ) -> PendingApproval: ...


class InMemoryApprovalStore:
    """Tenant-scoped reference store. Use a database-backed adapter in production."""

    def __init__(self) -> None:
        self._items: dict[str, dict[str, PendingApproval]] = {}

    def _bucket(self, scope: Scope) -> dict[str, PendingApproval]:
        return self._items.setdefault(scope.key, {})

    def save(self, approval: PendingApproval) -> PendingApproval:
        self._bucket(approval.scope)[approval.id] = approval.model_copy(deep=True)
        return approval

    def get(self, approval_id: str, scope: Scope) -> PendingApproval | None:
        item = self._bucket(scope).get(approval_id)
        return item.model_copy(deep=True) if item is not None else None

    def pending(self, scope: Scope) -> list[PendingApproval]:
        return [
            item.model_copy(deep=True)
            for item in self._bucket(scope).values()
            if item.status is ApprovalStatus.pending
        ]

    def decide(
        self, approval_id: str, scope: Scope, *, approved: bool, decided_by: str
    ) -> PendingApproval:
        approval = self.get(approval_id, scope)
        if approval is None:
            raise KeyError(approval_id)
        if approval.status is not ApprovalStatus.pending:
            raise ValueError("approval has already been decided")
        approval.status = ApprovalStatus.approved if approved else ApprovalStatus.rejected
        approval.decided_by = decided_by
        approval.decided_at = _utc_now()
        return self.save(approval)
