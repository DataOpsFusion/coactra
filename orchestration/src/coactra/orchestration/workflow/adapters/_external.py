"""Shared helpers for external workflow runtime adapters."""
from __future__ import annotations

import inspect
import uuid
from collections.abc import Callable
from typing import Any

from coactra.orchestration.workflow.domain.models import Procedure, RunResult
from coactra.orchestration.workflow.runtime.engine import RunContext
from coactra.orchestration.workflow.runtime.durable import (
    WorkflowInterrupt,
    WorkflowRun,
    WorkflowRunStatus,
)

ExternalPayloadFactory = Callable[
    [Procedure | None, dict[str, Any], RunContext, dict[str, Any] | None],
    dict[str, Any],
]


def default_external_payload(
    procedure: Procedure | None,
    state: dict[str, Any],
    ctx: RunContext,
    decision: dict[str, Any] | None,
) -> dict[str, Any]:
    """Build a JSON-shaped payload for host-owned workflow definitions."""

    payload: dict[str, Any] = {
        "state": dict(state),
        "scope": ctx.scope.model_dump(mode="json"),
    }
    if procedure is not None:
        payload["procedure"] = procedure.model_dump(mode="json")
    if decision is not None:
        payload["decision"] = dict(decision)
    if ctx.chain:
        payload["chain"] = list(ctx.chain)
    return payload


async def maybe_await(value: Any) -> Any:
    """Await ``value`` when an injected test fake or SDK call returns an awaitable."""

    if inspect.isawaitable(value):
        return await value
    return value


def new_thread_id(ctx: RunContext, procedure: Procedure | None = None) -> str:
    """Create a readable, unique workflow id without depending on a runtime."""

    name = procedure.name if procedure is not None else "workflow"
    safe_name = "".join(ch if ch.isalnum() or ch in "-_" else "-" for ch in name)
    safe_scope = "".join(ch if ch.isalnum() or ch in "-_" else "-" for ch in ctx.scope.key)
    return f"coactra-{safe_scope}-{safe_name}-{uuid.uuid4().hex}"


def normalize_external_run(
    value: Any,
    *,
    thread_id: str,
    state: dict[str, Any] | None = None,
) -> WorkflowRun:
    """Normalize a host runtime result into Coactra's serializable snapshot."""

    base_state = dict(state or {})
    if isinstance(value, WorkflowRun):
        return value
    if isinstance(value, dict):
        return _normalize_mapping(value, thread_id=thread_id, state=base_state)
    return _normalize_object(value, thread_id=thread_id, state=base_state)


def _normalize_mapping(
    value: dict[str, Any],
    *,
    thread_id: str,
    state: dict[str, Any],
) -> WorkflowRun:
    mapped_status = _status_from(value.get("status"))
    run_thread_id = str(value.get("thread_id") or thread_id)
    run_state = _mapping_or_default(value.get("state"), state)
    if mapped_status is None:
        if "output" in value or "path" in value:
            result = RunResult(
                output=_mapping_or_default(value.get("output"), run_state),
                path=list(value.get("path") or []),
            )
            return WorkflowRun(
                thread_id=run_thread_id,
                status=WorkflowRunStatus.completed,
                result=result,
                state=result.output,
            )
        return WorkflowRun(
            thread_id=run_thread_id,
            status=WorkflowRunStatus.running,
            state=run_state,
        )

    interrupt = _interrupt_from(value.get("interrupt"))
    result = _result_from(value.get("result"))
    if result is None and mapped_status is WorkflowRunStatus.completed:
        output = value.get("output", run_state)
        result = RunResult(
            output=_mapping_or_default(output, run_state),
            path=list(value.get("path") or []),
        )
    return WorkflowRun(
        thread_id=run_thread_id,
        status=mapped_status,
        result=result,
        interrupt=interrupt,
        state=run_state,
    )


def _normalize_object(value: Any, *, thread_id: str, state: dict[str, Any]) -> WorkflowRun:
    external_id = getattr(value, "id", None)
    if external_id is not None:
        state = {**state, "external_run_id": str(external_id)}
    status_obj = getattr(value, "state", None)
    if status_obj is None:
        return WorkflowRun(thread_id=thread_id, status=WorkflowRunStatus.running, state=state)
    if _call_bool(status_obj, "is_completed"):
        return WorkflowRun(
            thread_id=thread_id,
            status=WorkflowRunStatus.completed,
            result=RunResult(output=state, path=[]),
            state=state,
        )
    if _call_bool(status_obj, "is_failed") or _call_bool(status_obj, "is_crashed"):
        return WorkflowRun(thread_id=thread_id, status=WorkflowRunStatus.failed, state=state)
    return WorkflowRun(thread_id=thread_id, status=WorkflowRunStatus.running, state=state)


def _mapping_or_default(value: Any, default: dict[str, Any]) -> dict[str, Any]:
    if isinstance(value, dict):
        return dict(value)
    return dict(default)


def _status_from(value: Any) -> WorkflowRunStatus | None:
    if isinstance(value, WorkflowRunStatus):
        return value
    if value is None:
        return None
    text = str(value).lower()
    aliases = {
        "complete": WorkflowRunStatus.completed,
        "completed": WorkflowRunStatus.completed,
        "success": WorkflowRunStatus.completed,
        "succeeded": WorkflowRunStatus.completed,
        "failed": WorkflowRunStatus.failed,
        "failure": WorkflowRunStatus.failed,
        "crashed": WorkflowRunStatus.failed,
        "running": WorkflowRunStatus.running,
        "pending": WorkflowRunStatus.running,
        "scheduled": WorkflowRunStatus.running,
        "queued": WorkflowRunStatus.running,
        "interrupted": WorkflowRunStatus.interrupted,
        "paused": WorkflowRunStatus.interrupted,
    }
    return aliases.get(text)


def _interrupt_from(value: Any) -> WorkflowInterrupt | None:
    if isinstance(value, WorkflowInterrupt):
        return value
    if isinstance(value, dict):
        return WorkflowInterrupt(**value)
    return None


def _result_from(value: Any) -> RunResult | None:
    if isinstance(value, RunResult):
        return value
    if isinstance(value, dict):
        return RunResult(**value)
    return None


def _call_bool(obj: Any, method_name: str) -> bool:
    method = getattr(obj, method_name, None)
    if callable(method):
        return bool(method())
    return False
