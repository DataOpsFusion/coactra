"""Experimental MCP Tasks translation for durable work orders.

The internal work ledger remains the source of truth. This adapter exposes compatible
task-shaped views without coupling orchestration to a particular MCP server framework.
"""

from __future__ import annotations

from enum import StrEnum

from pydantic import BaseModel, ConfigDict, Field

from coactra.scope import Scope
from coactra.workflow.ledger.domain.models import (
    PAUSED_STATUSES,
    TERMINAL_STATUSES,
    WorkOrder,
    WorkStatus,
)
from coactra.workflow.ledger.service import WorkManager


class MCPTaskStatus(StrEnum):
    working = "working"
    input_required = "input_required"
    completed = "completed"
    failed = "failed"
    cancelled = "cancelled"


class MCPTask(BaseModel):
    """MCP `Task` wire shape with Python-friendly attribute names."""

    model_config = ConfigDict(populate_by_name=True)

    task_id: str = Field(alias="taskId")
    status: MCPTaskStatus
    status_message: str = Field(default="", alias="statusMessage")
    created_at: str = Field(alias="createdAt")
    last_updated_at: str = Field(alias="lastUpdatedAt")
    ttl: int | None = None
    poll_interval: int | None = Field(default=None, alias="pollInterval")


class MCPTaskPage(BaseModel):
    tasks: list[MCPTask]
    next_cursor: str | None = Field(default=None, alias="nextCursor")


class MCPTaskNotTerminalError(RuntimeError):
    """Raised when a caller asks for a result that is not ready."""


def to_mcp_task(
    order: WorkOrder,
    *,
    ttl: int | None = None,
    poll_interval: int | None = None,
) -> MCPTask:
    """Convert one durable order into the MCP Tasks status vocabulary."""

    if order.status in PAUSED_STATUSES:
        status = MCPTaskStatus.input_required
    elif order.status is WorkStatus.completed:
        status = MCPTaskStatus.completed
    elif order.status is WorkStatus.failed:
        status = MCPTaskStatus.failed
    elif order.status is WorkStatus.cancelled:
        status = MCPTaskStatus.cancelled
    else:
        status = MCPTaskStatus.working
    pending = order.pending_request
    message = pending.prompt if pending is not None else order.error or order.title
    return MCPTask(
        taskId=order.id,
        status=status,
        statusMessage=message,
        createdAt=order.created_at.isoformat(),
        lastUpdatedAt=order.updated_at.isoformat(),
        ttl=ttl,
        pollInterval=poll_interval,
    )


class MCPTasksAdapter:
    """Scope-bound operations needed by an MCP Tasks transport implementation."""

    def __init__(
        self,
        work: WorkManager,
        *,
        ttl: int | None = None,
        poll_interval: int | None = None,
    ) -> None:
        self._work = work
        self._ttl = ttl
        self._poll_interval = poll_interval

    def get(self, task_id: str, scope: Scope) -> MCPTask:
        return self._task(self._work.get(task_id, scope))

    def list(self, scope: Scope) -> MCPTaskPage:
        return MCPTaskPage(tasks=[self._task(order) for order in self._work.list(scope)])

    def cancel(self, task_id: str, scope: Scope, *, reason: str = "") -> MCPTask:
        return self._task(self._work.cancel(task_id, scope, reason=reason))

    def result(self, task_id: str, scope: Scope) -> WorkOrder:
        order = self._work.get(task_id, scope)
        if order.status not in TERMINAL_STATUSES:
            raise MCPTaskNotTerminalError(f"task {task_id!r} is still {order.status.value}")
        return order

    def _task(self, order: WorkOrder) -> MCPTask:
        return to_mcp_task(
            order,
            ttl=self._ttl,
            poll_interval=self._poll_interval,
        )
