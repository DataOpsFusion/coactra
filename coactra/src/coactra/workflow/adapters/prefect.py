"""Prefect deployment adapter for Coactra workflow runs.

Prefect owns deployment metadata, work pools, flow runs, retries, and UI/automation.
This adapter starts deployment runs with Coactra payloads. Resume is modeled as a new
Prefect deployment run carrying the previous Coactra thread id, state, and decision;
host flow code must decide how to apply that payload.
"""

from __future__ import annotations

from collections.abc import Callable
from typing import Any

from coactra.workflow.adapters._external import (
    ExternalPayloadFactory,
    default_external_payload,
    maybe_await,
    new_thread_id,
    normalize_external_run,
)
from coactra.workflow.adapters._stub import MissingExtraError
from coactra.workflow.domain.models import Procedure
from coactra.workflow.runtime import RunContext, WorkflowRun

RunDeployment = Callable[..., Any]
IdempotencyKeyFactory = Callable[[str, str, dict[str, Any]], str | None]


class PrefectEngine:
    """Start Coactra workflow runs through a Prefect deployment."""

    satisfies = "WorkflowEngine"
    resume_semantics = "new-run-with-prior-state"

    def __init__(
        self,
        *,
        deployment_name: str,
        run_deployment: RunDeployment | None = None,
        timeout: float | None = 0,
        poll_interval: float | None = 5,
        tags: list[str] | None = None,
        work_queue_name: str | None = None,
        as_subflow: bool | None = False,
        job_variables: dict[str, Any] | None = None,
        payload_factory: ExternalPayloadFactory | None = None,
        idempotency_key_factory: IdempotencyKeyFactory | None = None,
        run_options: dict[str, Any] | None = None,
    ) -> None:
        self._deployment_name = deployment_name
        self._run_deployment = run_deployment
        self._timeout = timeout
        self._poll_interval = poll_interval
        self._tags = list(tags or [])
        self._work_queue_name = work_queue_name
        self._as_subflow = as_subflow
        self._job_variables = dict(job_variables or {})
        self._payload_factory = payload_factory or default_external_payload
        self._idempotency_key_factory = idempotency_key_factory or _default_idempotency_key
        self._run_options = dict(run_options or {})

    async def start(
        self,
        procedure: Procedure,
        state: dict[str, Any],
        ctx: RunContext,
        *,
        thread_id: str | None = None,
    ) -> WorkflowRun:
        logical_thread_id = thread_id or new_thread_id(ctx, procedure)
        payload = self._payload_factory(procedure, state, ctx, None)
        payload.update(
            {
                "coactra_action": "start",
                "coactra_thread_id": logical_thread_id,
                "resume_semantics": self.resume_semantics,
            }
        )
        raw = await self._run(
            payload,
            action="start",
            thread_id=logical_thread_id,
            flow_run_name=logical_thread_id,
        )
        return normalize_external_run(
            raw,
            thread_id=logical_thread_id,
            state=self._state(ctx, logical_thread_id, raw),
        )

    async def resume(
        self,
        thread_id: str,
        ctx: RunContext,
        *,
        procedure: Procedure | None = None,
        decision: dict[str, Any] | None = None,
        state: dict[str, Any] | None = None,
    ) -> WorkflowRun:
        payload = self._payload_factory(procedure, state or {}, ctx, decision)
        payload.update(
            {
                "coactra_action": "resume",
                "coactra_thread_id": thread_id,
                "coactra_resume_thread_id": thread_id,
                "resume_semantics": self.resume_semantics,
            }
        )
        raw = await self._run(
            payload,
            action="resume",
            thread_id=thread_id,
            flow_run_name=f"{thread_id}-resume",
        )
        return normalize_external_run(
            raw,
            thread_id=thread_id,
            state=self._state(ctx, thread_id, raw),
        )

    async def _run(
        self,
        payload: dict[str, Any],
        *,
        action: str,
        thread_id: str,
        flow_run_name: str,
    ) -> Any:
        runner = self._load_runner()
        options: dict[str, Any] = {
            "name": self._deployment_name,
            "parameters": payload,
            "flow_run_name": flow_run_name,
            "timeout": self._timeout,
            "poll_interval": self._poll_interval,
            "as_subflow": self._as_subflow,
            **self._run_options,
        }
        if self._tags:
            options["tags"] = self._tags
        if self._work_queue_name is not None:
            options["work_queue_name"] = self._work_queue_name
        if self._job_variables:
            options["job_variables"] = self._job_variables
        idempotency_key = self._idempotency_key_factory(action, thread_id, payload)
        if idempotency_key:
            options["idempotency_key"] = idempotency_key
        return await maybe_await(runner(**options))

    def _load_runner(self) -> RunDeployment:
        if self._run_deployment is not None:
            return self._run_deployment
        try:
            from prefect.deployments import run_deployment
        except ImportError as exc:  # pragma: no cover - depends on optional extra
            raise MissingExtraError(
                "PrefectEngine requires coactra[prefect] or an injected run_deployment callable"
            ) from exc
        return run_deployment

    def _state(self, ctx: RunContext, thread_id: str, raw: Any) -> dict[str, Any]:
        result = {
            "tenant_scope": ctx.scope.key,
            "prefect_deployment_name": self._deployment_name,
            "coactra_thread_id": thread_id,
            "resume_semantics": self.resume_semantics,
        }
        flow_run_id = getattr(raw, "id", None)
        if flow_run_id is not None:
            result["prefect_flow_run_id"] = str(flow_run_id)
        return result


def _default_idempotency_key(action: str, thread_id: str, payload: dict[str, Any]) -> str | None:
    if action == "start":
        return thread_id
    return None


__all__ = ["PrefectEngine"]
