"""Temporal ``WorkflowEngine`` adapter.

Temporal owns durable workflow history, retries, replay, workers, and signals. This
adapter only translates Coactra's stable ``WorkflowEngine`` payloads to Temporal client
calls so host workflow definitions can stay runtime-specific.
"""
from __future__ import annotations

from typing import Any

from coactra.jobs.workflow.adapters._external import (
    ExternalPayloadFactory,
    default_external_payload,
    maybe_await,
    new_thread_id,
    normalize_external_run,
)
from coactra.jobs.workflow.adapters._stub import MissingExtraError
from coactra.jobs.workflow.domain.models import Procedure
from coactra.jobs.workflow.runtime import (
    RunContext,
    WorkflowRun,
    WorkflowRunStatus,
)


class TemporalEngine:
    """Start and resume Coactra workflow runs through a Temporal client."""

    satisfies = "WorkflowEngine"
    resume_semantics = "same-thread"

    def __init__(
        self,
        *,
        client: Any,
        workflow: Any,
        task_queue: str,
        signal_name: str = "resume",
        wait_for_result: bool = False,
        payload_factory: ExternalPayloadFactory | None = None,
        start_options: dict[str, Any] | None = None,
        signal_options: dict[str, Any] | None = None,
    ) -> None:
        self._client = client
        self._workflow = workflow
        self._task_queue = task_queue
        self._signal_name = signal_name
        self._wait_for_result = wait_for_result
        self._payload_factory = payload_factory or default_external_payload
        self._start_options = dict(start_options or {})
        self._signal_options = dict(signal_options or {})

    @classmethod
    async def connect(
        cls,
        target_host: str,
        *,
        workflow: Any,
        task_queue: str,
        namespace: str = "default",
        **connect_options: Any,
    ) -> "TemporalEngine":
        """Connect a Temporal client lazily and return a configured adapter."""

        try:
            from temporalio.client import Client
        except ImportError as exc:  # pragma: no cover - depends on optional extra
            raise MissingExtraError(
                "TemporalEngine.connect requires coactra-jobs[temporal]"
            ) from exc
        client = await Client.connect(target_host, namespace=namespace, **connect_options)
        return cls(client=client, workflow=workflow, task_queue=task_queue)

    async def start(
        self,
        procedure: Procedure,
        state: dict[str, Any],
        ctx: RunContext,
        *,
        thread_id: str | None = None,
    ) -> WorkflowRun:
        workflow_id = thread_id or new_thread_id(ctx, procedure)
        payload = self._payload_factory(procedure, state, ctx, None)
        handle = await maybe_await(
            self._client.start_workflow(
                self._workflow,
                payload,
                id=workflow_id,
                task_queue=self._task_queue,
                **self._start_options,
            )
        )
        return await self._snapshot(handle, thread_id=workflow_id, ctx=ctx)

    async def resume(
        self,
        thread_id: str,
        ctx: RunContext,
        *,
        procedure: Procedure | None = None,
        decision: dict[str, Any] | None = None,
        state: dict[str, Any] | None = None,
    ) -> WorkflowRun:
        handle = self._client.get_workflow_handle(thread_id)
        payload = self._payload_factory(procedure, state or {}, ctx, decision)
        await maybe_await(handle.signal(self._signal_name, payload, **self._signal_options))
        return await self._snapshot(handle, thread_id=thread_id, ctx=ctx, signaled=True)

    async def _snapshot(
        self,
        handle: Any,
        *,
        thread_id: str,
        ctx: RunContext,
        signaled: bool = False,
    ) -> WorkflowRun:
        workflow_id = str(getattr(handle, "id", thread_id) or thread_id)
        run_state = {
            "tenant_scope": ctx.scope.key,
            "temporal_workflow_id": workflow_id,
            "resume_semantics": self.resume_semantics,
        }
        run_id = getattr(handle, "run_id", None)
        if run_id:
            run_state["temporal_run_id"] = str(run_id)
        if signaled:
            run_state["temporal_signal"] = self._signal_name
        if self._wait_for_result:
            raw = await maybe_await(handle.result())
            return normalize_external_run(raw, thread_id=workflow_id, state=run_state)
        return WorkflowRun(
            thread_id=workflow_id,
            status=WorkflowRunStatus.running,
            state=run_state,
        )


__all__ = ["TemporalEngine"]
