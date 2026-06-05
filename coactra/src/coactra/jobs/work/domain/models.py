"""Durable work-order models.

A procedure describes how work can be done. A WorkOrder records one real unit of work:
ownership, leases, attempts, outputs, pauses, checkpoints, and terminal outcome.
"""

from __future__ import annotations

import uuid
from datetime import datetime
from enum import StrEnum
from typing import Any, Literal

from pydantic import BaseModel, Field, model_validator

from coactra.jobs.work.domain.artifacts import Artifact
from coactra.jobs.work.domain.capabilities import CapabilityRequirement
from coactra.jobs.work.domain.events import AuditContext, utc_now
from coactra.jobs.work.domain.scope import Scope


class WorkStatus(StrEnum):
    queued = "queued"
    claimed = "claimed"
    running = "running"
    input_required = "input_required"
    auth_required = "auth_required"
    blocked = "blocked"
    completed = "completed"
    failed = "failed"
    cancelled = "cancelled"


TERMINAL_STATUSES = {WorkStatus.completed, WorkStatus.failed, WorkStatus.cancelled}
PAUSED_STATUSES = {WorkStatus.input_required, WorkStatus.auth_required, WorkStatus.blocked}


class AttemptStatus(StrEnum):
    running = "running"
    completed = "completed"
    failed = "failed"
    interrupted = "interrupted"


class DecisionOutcome(StrEnum):
    accepted = "accepted"
    declined = "declined"
    cancelled = "cancelled"


class RetryPolicy(BaseModel):
    max_attempts: int = Field(default=3, ge=1)
    backoff_seconds: float = Field(default=0.0, ge=0.0)


class Deadline(BaseModel):
    due_at: datetime

    def expired(self, *, at: datetime | None = None) -> bool:
        return (at or utc_now()) >= self.due_at


class Assignment(BaseModel):
    worker: str = Field(min_length=1)
    assigned_at: datetime = Field(default_factory=utc_now)


class Lease(BaseModel):
    id: str = Field(default_factory=lambda: uuid.uuid4().hex)
    work_id: str = Field(min_length=1)
    worker: str = Field(min_length=1)
    expires_at: datetime
    heartbeat_at: datetime = Field(default_factory=utc_now)

    def active(self, *, at: datetime | None = None) -> bool:
        return (at or utc_now()) < self.expires_at


class Attempt(BaseModel):
    id: str = Field(default_factory=lambda: uuid.uuid4().hex)
    number: int = Field(ge=1)
    worker: str = Field(min_length=1)
    status: AttemptStatus = AttemptStatus.running
    started_at: datetime = Field(default_factory=utc_now)
    finished_at: datetime | None = None
    error: str | None = None


class ResumeToken(BaseModel):
    value: str = Field(default_factory=lambda: uuid.uuid4().hex)
    work_id: str = Field(min_length=1)


class Checkpoint(BaseModel):
    token: ResumeToken
    state: dict[str, Any] = Field(default_factory=dict)
    created_at: datetime = Field(default_factory=utc_now)


class ApprovalRequest(BaseModel):
    kind: Literal["approval"] = "approval"
    id: str = Field(default_factory=lambda: uuid.uuid4().hex)
    prompt: str = Field(min_length=1)
    requested_at: datetime = Field(default_factory=utc_now)
    metadata: dict[str, Any] = Field(default_factory=dict)


class ElicitationRequest(BaseModel):
    kind: Literal["input", "auth"]
    id: str = Field(default_factory=lambda: uuid.uuid4().hex)
    prompt: str = Field(min_length=1)
    requested_at: datetime = Field(default_factory=utc_now)
    metadata: dict[str, Any] = Field(default_factory=dict)


PauseRequest = ApprovalRequest | ElicitationRequest


class Decision(BaseModel):
    request_id: str = Field(min_length=1)
    outcome: DecisionOutcome
    decided_by: str = Field(min_length=1)
    decided_at: datetime = Field(default_factory=utc_now)
    data: dict[str, Any] = Field(default_factory=dict)


class Usage(BaseModel):
    input_tokens: int = Field(default=0, ge=0)
    output_tokens: int = Field(default=0, ge=0)
    cost: float = Field(default=0.0, ge=0.0)

    @property
    def total_tokens(self) -> int:
        return self.input_tokens + self.output_tokens


class Budget(BaseModel):
    max_tokens: int | None = Field(default=None, ge=0)
    max_cost: float | None = Field(default=None, ge=0.0)
    max_attempts: int | None = Field(default=None, ge=1)

    def allows(self, usage: Usage, *, attempts: int) -> bool:
        return (
            (self.max_tokens is None or usage.total_tokens <= self.max_tokens)
            and (self.max_cost is None or usage.cost <= self.max_cost)
            and (self.max_attempts is None or attempts <= self.max_attempts)
        )


class WorkOrder(BaseModel):
    id: str = Field(default_factory=lambda: uuid.uuid4().hex)
    scope: Scope
    title: str = Field(min_length=1)
    description: str = ""
    procedure: str | None = None
    status: WorkStatus = WorkStatus.queued
    idempotency_key: str | None = None
    parent_id: str | None = None
    correlation_id: str | None = None
    audit_context: AuditContext = Field(default_factory=AuditContext)
    requirements: list[CapabilityRequirement] = Field(default_factory=list)
    retry_policy: RetryPolicy = Field(default_factory=RetryPolicy)
    deadline: Deadline | None = None
    budget: Budget | None = None
    assignment: Assignment | None = None
    lease: Lease | None = None
    attempts: list[Attempt] = Field(default_factory=list)
    artifacts: list[Artifact] = Field(default_factory=list)
    checkpoint: Checkpoint | None = None
    pending_request: PauseRequest | None = None
    decisions: list[Decision] = Field(default_factory=list)
    usage: Usage = Field(default_factory=Usage)
    error: str | None = None
    metadata: dict[str, Any] = Field(default_factory=dict)
    version: int = Field(default=0, ge=0)
    created_at: datetime = Field(default_factory=utc_now)
    updated_at: datetime = Field(default_factory=utc_now)

    @model_validator(mode="after")
    def _validate_terminal_state(self) -> "WorkOrder":
        if self.status in TERMINAL_STATUSES and self.lease is not None:
            raise ValueError("terminal work order may not retain a lease")
        return self
