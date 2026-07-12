"""Plan and receipt value types for reviewable work submission."""

from __future__ import annotations

import uuid
from datetime import datetime
from typing import Any

from pydantic import BaseModel, Field

from coactra.scope import Scope
from coactra.workflow.ledger.domain.capabilities import CapabilityRequirement
from coactra.workflow.ledger.domain.events import AuditContext, utc_now
from coactra.workflow.ledger.domain.models import WorkOrder, WorkStatus


class ExecutionPlan(BaseModel):
    """Reviewable intent that has not performed side effects."""

    id: str = Field(default_factory=lambda: uuid.uuid4().hex)
    scope: Scope
    title: str = Field(min_length=1)
    description: str = ""
    procedure: str | None = None
    idempotency_key: str | None = None
    requirements: list[CapabilityRequirement] = Field(default_factory=list)
    audit_context: AuditContext = Field(default_factory=AuditContext)
    metadata: dict[str, Any] = Field(default_factory=dict)
    created_at: datetime = Field(default_factory=utc_now)

    def to_order(self) -> WorkOrder:
        """Create the queued durable order represented by this plan."""

        return WorkOrder(
            scope=self.scope,
            title=self.title,
            description=self.description,
            procedure=self.procedure,
            idempotency_key=self.idempotency_key or f"plan:{self.id}",
            requirements=self.requirements,
            audit_context=self.audit_context,
            metadata={**self.metadata, "execution_plan_id": self.id},
        )


class ExecutionReceipt(BaseModel):
    """Stable handle returned when an execution plan enters the durable ledger."""

    plan_id: str
    work_order_id: str
    scope: Scope
    status: WorkStatus
    idempotency_key: str | None = None
    submitted_at: datetime

    @classmethod
    def from_order(cls, plan: ExecutionPlan, order: WorkOrder) -> ExecutionReceipt:
        return cls(
            plan_id=plan.id,
            work_order_id=order.id,
            scope=order.scope,
            status=order.status,
            idempotency_key=order.idempotency_key,
            submitted_at=order.created_at,
        )
