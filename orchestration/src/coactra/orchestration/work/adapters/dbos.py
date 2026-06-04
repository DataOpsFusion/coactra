"""DBOS bridge for lightweight database-backed durable dispatch.

DBOS already owns durable queues, recovery, idempotent workflow IDs, cancellation,
resume, fork, scheduling, and notifications. This adapter maps a Coactra WorkOrder into
DBOS Client enqueue options; it intentionally does not reimplement those features.
"""

from __future__ import annotations

from typing import Any

from coactra.orchestration.work.adapters._optional import optional_module
from coactra.orchestration.work.domain.models import WorkOrder


class DBOSDispatcher:
    """Submit and control Coactra work through an injected ``dbos.DBOSClient``."""

    def __init__(
        self,
        client: Any,
        *,
        workflow_name: str,
        queue_name: str,
        partition_by_scope: bool = False,
    ) -> None:
        self.client = client
        self.workflow_name = workflow_name
        self.queue_name = queue_name
        self.partition_by_scope = partition_by_scope

    @classmethod
    def connect(
        cls,
        *,
        system_database_url: str,
        workflow_name: str,
        queue_name: str,
        partition_by_scope: bool = False,
        **client_kwargs: Any,
    ) -> "DBOSDispatcher":
        dbos = optional_module("dbos", extra="dbos")
        client = dbos.DBOSClient(system_database_url=system_database_url, **client_kwargs)
        return cls(
            client,
            workflow_name=workflow_name,
            queue_name=queue_name,
            partition_by_scope=partition_by_scope,
        )

    def submit(self, order: WorkOrder, *args: Any, **kwargs: Any) -> str:
        """Enqueue one registered DBOS workflow and return its durable workflow ID."""
        options: dict[str, Any] = {
            "workflow_name": self.workflow_name,
            "queue_name": self.queue_name,
            "workflow_id": order.id,
        }
        if order.idempotency_key:
            options["deduplication_id"] = order.idempotency_key
        if self.partition_by_scope:
            options["queue_partition_key"] = order.scope.key
        handle = self.client.enqueue(options, order.model_dump(mode="json"), *args, **kwargs)
        return handle.get_workflow_id()

    def status(self, work_id: str) -> Any:
        return self.client.retrieve_workflow(work_id).get_status()

    def result(self, work_id: str) -> Any:
        return self.client.retrieve_workflow(work_id).get_result()

    def cancel(self, work_id: str) -> None:
        self.client.cancel_workflow(work_id)

    def resume(self, work_id: str) -> Any:
        return self.client.resume_workflow(work_id, queue_name=self.queue_name)

    def fork(self, work_id: str, *, start_step: int) -> Any:
        return self.client.fork_workflow(work_id, start_step, queue_name=self.queue_name)

    def send(self, work_id: str, message: Any, *, topic: str | None = None) -> None:
        self.client.send(work_id, message, topic=topic)
