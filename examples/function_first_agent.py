"""Function-first Coactra sample.

This example shows the intended app style when you do not want a class-heavy design:
plain functions build behavior, small structural ports adapt functions to Coactra, and
stateful classes are kept at durable boundaries such as WorkManager.

Run after installing the local packages in editable mode or through the repo package env.
"""

from __future__ import annotations

import asyncio
import hashlib
from collections.abc import Sequence
from pprint import pprint
from types import SimpleNamespace
from typing import Any

from coactra.agent import Scope as AgentScope
from coactra.agent import make_agent
from coactra.orchestration.work import Scope as WorkScope
from coactra.orchestration.work import WorkManager, WorkOrder


def to_work_scope(scope: AgentScope) -> WorkScope:
    """Convert the agent scope into the work-order scope shape."""
    return WorkScope(tenant_id=scope.tenant_id, namespace=scope.namespace)


def make_ai_port():
    """A tiny AIPort without defining an adapter class."""

    def ask(prompt: str) -> str:
        return f"draft answer for: {prompt}"

    def structured(schema: type[Any], prompt: str) -> Any:  # noqa: ARG001
        return schema()

    return SimpleNamespace(ask=ask, structured=structured)


def make_memory_port():
    """A small async memory port backed by a list."""
    rows: list[dict[str, str]] = []

    async def remember(events: Sequence[Any], scope: AgentScope) -> None:
        rows.extend({"scope": scope.key, "text": str(event)} for event in events)

    async def recall(query: str, scope: AgentScope, k: int = 10) -> list[dict[str, str]]:
        needle = query.lower()
        matches = [
            row
            for row in rows
            if row["scope"] == scope.key and needle in row["text"].lower()
        ]
        return matches[:k]

    return SimpleNamespace(remember=remember, recall=recall)


def make_workspace_port():
    """An in-memory WorkspacePort for demos and tests."""
    files: dict[str, str] = {}

    def write(path: str, data: str) -> None:
        files[path] = data

    def read(path: str) -> str:
        return files.get(path, "")

    def run(command: str | Sequence[str]) -> dict[str, Any]:
        return {"command": command, "exit_code": 0, "stdout": "dry-run"}

    return SimpleNamespace(write=write, read=read, run=run)


def make_work_port(manager: WorkManager):
    """Adapt WorkManager to the agent WorkPort without subclassing anything."""

    def submit(order: WorkOrder) -> WorkOrder:
        return manager.submit(order)

    def get(work_id: str, scope: AgentScope) -> WorkOrder:
        return manager.get(work_id, to_work_scope(scope))

    def cancel(work_id: str, scope: AgentScope, *, reason: str = "") -> WorkOrder:
        return manager.cancel(work_id, to_work_scope(scope), reason=reason)

    return SimpleNamespace(submit=submit, get=get, cancel=cancel)


def make_workflow_port():
    """The workflow port can be a function wrapper until you need a real engine."""

    def run(procedure: Any, state: dict[str, Any]) -> dict[str, Any]:
        return {"procedure": str(procedure), "state": state, "ran": True}

    return SimpleNamespace(run=run)


def make_organization_port():
    """A permissive organization policy for the sample."""

    def can(member: Any, action: Any) -> bool:  # noqa: ARG001
        return action != "deploy_prod"

    def manager(node: Any) -> None:  # noqa: ARG001
        return None

    def members(node: Any) -> list[Any]:  # noqa: ARG001
        return []

    return SimpleNamespace(can=can, manager=manager, members=members)


def build_support_agent(*, tenant_id: str = "acme"):
    """Composition root for this app. It returns useful objects, not a subclass tree."""
    scope = AgentScope(tenant_id=tenant_id, namespace="agent:support")
    work_manager = WorkManager()
    agent = make_agent(
        scope=scope,
        me="agent:support",
        ai=make_ai_port(),
        memory=make_memory_port(),
        workspace=make_workspace_port(),
        workflow=make_workflow_port(),
        organization=make_organization_port(),
        work=make_work_port(work_manager),
    )
    return agent, work_manager


def idempotency_key(text: str) -> str:
    digest = hashlib.sha256(text.encode("utf-8")).hexdigest()[:16]
    return f"incident:{digest}"


async def triage_incident(agent, incident_text: str) -> dict[str, Any]:
    """Application behavior as a plain function."""
    await agent.remember([incident_text])
    agent.workspace_write("incidents/latest.txt", incident_text)

    order = agent.submit_work(
        WorkOrder(
            scope=to_work_scope(agent.scope),
            title=f"Triage incident: {incident_text[:48]}",
            idempotency_key=idempotency_key(incident_text),
        )
    )
    draft = agent.think(f"What should we check first? {incident_text}")
    workflow_result = agent.run_procedure("triage", {"work_id": order.id})

    return {
        "work_id": order.id,
        "status": order.status.value,
        "draft": draft,
        "workflow": workflow_result,
        "workspace_note": agent.workspace_read("incidents/latest.txt"),
    }


async def main() -> None:
    agent, _work_manager = build_support_agent()
    result = await triage_incident(agent, "database latency is high after deploy")
    recalled = await agent.recall("database")
    pprint({"result": result, "recalled": recalled})


if __name__ == "__main__":
    asyncio.run(main())
