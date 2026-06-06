"""Support ticket agent composed from small ports.

Use this when you want to see the dependency-injection shape without subclassing
an agent framework. The ports are local and deterministic so the script runs in
CI and in a fresh checkout.
"""

from __future__ import annotations

import asyncio
import hashlib
from collections.abc import Sequence
from pprint import pprint
from types import SimpleNamespace
from typing import Any

from coactra.agent import Scope as AgentScope, make_agent
from coactra.jobs import Scope as WorkScope, WorkManager, WorkOrder


def to_work_scope(scope: AgentScope) -> WorkScope:
    return WorkScope(tenant_id=scope.tenant_id, namespace="support-tickets")


def ticket_key(ticket_id: str) -> str:
    digest = hashlib.sha256(ticket_id.encode("utf-8")).hexdigest()[:12]
    return f"ticket:{digest}"


def local_ai_port():
    def ask(prompt: str) -> str:
        return f"reply: check auth headers, worker logs, and the most recent deploy. ({prompt})"

    def structured(schema: type[Any], prompt: str) -> Any:  # noqa: ARG001
        return schema()

    return SimpleNamespace(ask=ask, structured=structured)


def local_memory_port():
    rows: list[dict[str, str]] = []

    async def remember(events: Sequence[Any], scope: AgentScope) -> None:
        rows.extend({"scope": scope.key, "text": str(event)} for event in events)

    async def recall(query: str, scope: AgentScope, k: int = 5) -> list[dict[str, str]]:
        needle = query.lower()
        return [
            row
            for row in rows
            if row["scope"] == scope.key and needle in row["text"].lower()
        ][:k]

    return SimpleNamespace(remember=remember, recall=recall)


def local_workspace_port():
    files: dict[str, str] = {}

    def write(path: str, data: str) -> None:
        files[path] = data

    def read(path: str) -> str:
        return files.get(path, "")

    def run(command: str | Sequence[str]) -> dict[str, Any]:
        return {"command": list(command) if not isinstance(command, str) else command, "exit_code": 0}

    return SimpleNamespace(write=write, read=read, run=run)


def work_port(manager: WorkManager):
    def submit(order: WorkOrder) -> WorkOrder:
        return manager.submit(order)

    def get(work_id: str, scope: AgentScope) -> WorkOrder:
        return manager.get(work_id, to_work_scope(scope))

    def cancel(work_id: str, scope: AgentScope, *, reason: str = "") -> WorkOrder:
        return manager.cancel(work_id, to_work_scope(scope), reason=reason)

    return SimpleNamespace(submit=submit, get=get, cancel=cancel)


def build_agent() -> tuple[Any, WorkManager]:
    scope = AgentScope(tenant_id="acme", namespace="agent:support")
    work = WorkManager()
    agent = make_agent(
        scope=scope,
        me="agent:support",
        ai=local_ai_port(),
        memory=local_memory_port(),
        workspace=local_workspace_port(),
        work=work_port(work),
    )
    return agent, work


async def handle_ticket(ticket_id: str, issue: str) -> dict[str, object]:
    agent, work = build_agent()

    await agent.remember(["Prior fix: rotate API key, then restart the billing worker."])
    recalled = await agent.recall("API key")
    prior = recalled[0]["text"] if recalled else "No prior fix found."

    agent.workspace_write("tickets/latest.md", f"# {ticket_id}\n{issue}\n")
    order = agent.submit_work(
        WorkOrder(
            scope=to_work_scope(agent.scope),
            title=f"Resolve {ticket_id}: {issue[:64]}",
            idempotency_key=ticket_key(ticket_id),
        )
    )
    draft = agent.think(f"Issue: {issue}. Prior context: {prior}")

    return {
        "ticket_id": ticket_id,
        "work_id": order.id,
        "status": work.get(order.id, to_work_scope(agent.scope)).status.value,
        "draft": draft,
        "workspace_note": agent.workspace_read("tickets/latest.md").strip(),
    }


async def main() -> None:
    pprint(await handle_ticket("T-1842", "billing worker rejects API key after deploy"))


if __name__ == "__main__":
    asyncio.run(main())
