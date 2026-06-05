"""CloudEvents-shaped audit envelopes emitted for every work transition."""

from __future__ import annotations

import uuid
from datetime import datetime, timezone
from typing import Any

from pydantic import BaseModel, Field


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


class AuditContext(BaseModel):
    """Non-secret correlation metadata copied into each work transition event."""

    trace_id: str | None = None
    agent_id: str | None = None
    department_id: str | None = None
    policy_decision_id: str | None = None
    delegation_chain: list[str] = Field(default_factory=list)

    def event_data(self) -> dict[str, Any]:
        return self.model_dump(exclude_none=True)


class EventEnvelope(BaseModel):
    """A small CloudEvents-compatible event vocabulary."""

    specversion: str = "1.0"
    id: str = Field(default_factory=lambda: uuid.uuid4().hex)
    source: str = "coactra.jobs"
    type: str = Field(min_length=1)
    time: datetime = Field(default_factory=utc_now)
    subject: str | None = None
    tenant_id: str = Field(min_length=1)
    data: dict[str, Any] = Field(default_factory=dict)
