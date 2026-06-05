"""Temporal bridge for server-backed durable execution.

Temporal owns workflow history, retries, timers, signals, activities, and recovery. This
small async dispatcher only submits and controls WorkOrder payloads through a configured
Temporal client.
"""

from __future__ import annotations

from typing import Any

from coactra.jobs.work.adapters._optional import optional_module
from coactra.jobs.work.domain.models import WorkOrder


class TemporalDispatcher:
    """Submit and signal Coactra work through an injected ``temporalio`` client."""

    def __init__(self, client: Any, *, workflow: Any, task_queue: str) -> None:
        self.client = client
        self.workflow = workflow
        self.task_queue = task_queue

    @classmethod
    async def connect(
        cls,
        target_host: str,
        *,
        workflow: Any,
        task_queue: str,
        **connect_kwargs: Any,
    ) -> "TemporalDispatcher":
        client_module = optional_module("temporalio.client", extra="temporal")
        client = await client_module.Client.connect(target_host, **connect_kwargs)
        return cls(client, workflow=workflow, task_queue=task_queue)

    async def submit(self, order: WorkOrder) -> Any:
        """Start one Temporal workflow, using the Coactra ID as Temporal workflow ID."""
        payload = order.model_dump(mode="json")
        return await self.client.start_workflow(
            self.workflow,
            payload,
            id=order.id,
            task_queue=self.task_queue,
        )

    def handle(self, work_id: str) -> Any:
        return self.client.get_workflow_handle(work_id)

    async def cancel(self, work_id: str) -> None:
        await self.handle(work_id).cancel()

    async def signal(self, work_id: str, signal: str, arg: Any | None = None) -> None:
        handle = self.handle(work_id)
        if arg is None:
            await handle.signal(signal)
        else:
            await handle.signal(signal, arg)

    async def result(self, work_id: str) -> Any:
        return await self.handle(work_id).result()
