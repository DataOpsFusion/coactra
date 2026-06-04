"""Dapr Workflow bridge for sidecar-backed durable execution."""

from __future__ import annotations

from typing import Any

from coactra.orchestration.work.adapters._optional import optional_module
from coactra.orchestration.work.domain.models import WorkOrder


class DaprDispatcher:
    """Submit and control work through ``dapr.ext.workflow.DaprWorkflowClient``."""

    def __init__(self, client: Any, *, workflow: Any) -> None:
        self.client = client
        self.workflow = workflow

    @classmethod
    def connect(cls, *, workflow: Any, **client_kwargs: Any) -> "DaprDispatcher":
        dapr = optional_module("dapr.ext.workflow", extra="dapr")
        return cls(dapr.DaprWorkflowClient(**client_kwargs), workflow=workflow)

    def submit(self, order: WorkOrder) -> str:
        return self.client.schedule_new_workflow(
            workflow=self.workflow,
            input=order.model_dump(mode="json"),
            instance_id=order.id,
        )

    def status(self, work_id: str) -> Any:
        return self.client.get_workflow_state(instance_id=work_id)

    def pause(self, work_id: str) -> None:
        self.client.pause_workflow(instance_id=work_id)

    def resume(self, work_id: str) -> None:
        self.client.resume_workflow(instance_id=work_id)

    def signal(self, work_id: str, event: str, data: Any | None = None) -> None:
        self.client.raise_workflow_event(instance_id=work_id, event_name=event, data=data)

    def cancel(self, work_id: str) -> None:
        self.client.terminate_workflow(instance_id=work_id)

    def purge(self, work_id: str) -> None:
        self.client.purge_workflow(instance_id=work_id)
