"""Async durable workflow boundary.

The library owns the stable start/resume contract, not durable execution itself.
Temporal, a host workflow runtime, or another durable engine can implement this Protocol.
``AsyncProcedureRunnerAdapter`` is an honest bridge for local run-to-completion engines:
it supports async start but deliberately rejects resume.
"""
from __future__ import annotations

import uuid
from enum import Enum
from typing import Any, Protocol, runtime_checkable

from pydantic import BaseModel, Field

from coactra.orchestration.workflow.domain.models import Procedure, RunResult
from coactra.orchestration.workflow.runtime.engine import ProcedureRunner, RunContext


class WorkflowRunStatus(str, Enum):
    running = "running"
    interrupted = "interrupted"
    completed = "completed"
    failed = "failed"


class WorkflowInterrupt(BaseModel):
    """Persistable reason a durable engine stopped and needs an external decision."""

    kind: str = Field(min_length=1)
    step_id: str = Field(min_length=1)
    prompt: str = Field(min_length=1)
    metadata: dict[str, Any] = Field(default_factory=dict)


class WorkflowRun(BaseModel):
    """Serializable durable-run snapshot returned by start/resume operations."""

    thread_id: str = Field(min_length=1)
    status: WorkflowRunStatus
    result: RunResult | None = None
    interrupt: WorkflowInterrupt | None = None
    state: dict[str, Any] = Field(default_factory=dict)


class WorkflowNotResumableError(RuntimeError):
    """Raised when resume is attempted against a run-to-completion adapter."""


@runtime_checkable
class WorkflowEngine(Protocol):
    """Durable execution SPI. Implementations persist engine state behind ``thread_id``."""

    async def start(
        self,
        procedure: Procedure,
        state: dict[str, Any],
        ctx: RunContext,
        *,
        thread_id: str | None = None,
    ) -> WorkflowRun:
        """Start or idempotently attach to one durable workflow thread."""
        ...

    async def resume(
        self,
        thread_id: str,
        ctx: RunContext,
        *,
        procedure: Procedure | None = None,
        decision: dict[str, Any] | None = None,
        state: dict[str, Any] | None = None,
    ) -> WorkflowRun:
        """Resume a persisted workflow thread after an interrupt or external event.

        ``procedure`` lets graph-backed runtimes rebuild their executable graph after a
        process restart. Engines such as Temporal that persist the workflow type behind
        ``thread_id`` may ignore it.
        """
        ...


class AsyncProcedureRunnerAdapter:
    """Expose a local synchronous runner through async start without fake durability."""

    def __init__(self, runner: ProcedureRunner) -> None:
        self._runner = runner
        self._runs: dict[str, WorkflowRun] = {}

    async def start(
        self,
        procedure: Procedure,
        state: dict[str, Any],
        ctx: RunContext,
        *,
        thread_id: str | None = None,
    ) -> WorkflowRun:
        thread_id = thread_id or uuid.uuid4().hex
        existing = self._runs.get(thread_id)
        if existing is not None:
            return existing
        result = self._runner.run(procedure, state, ctx)
        run = WorkflowRun(
            thread_id=thread_id,
            status=WorkflowRunStatus.completed,
            result=result,
            state=result.output,
        )
        self._runs[thread_id] = run
        return run

    async def resume(
        self,
        thread_id: str,
        ctx: RunContext,
        *,
        procedure: Procedure | None = None,
        decision: dict[str, Any] | None = None,
        state: dict[str, Any] | None = None,
    ) -> WorkflowRun:
        raise WorkflowNotResumableError(
            "local ProcedureRunner adapters are run-to-completion; inject a durable "
            "WorkflowEngine such as the host runtime or Temporal to resume threads"
        )
