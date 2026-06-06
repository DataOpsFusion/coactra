"""Ticket triage with agent, memory, and durable work.

This is the copyable project example. It keeps app behavior in plain functions and
puts persistence behind Memory and WorkManager.
"""

from __future__ import annotations

import hashlib
from pprint import pprint

from coactra.agent import Scope as AgentScope, make_agent
from coactra.jobs import Scope as WorkScope, WorkManager, WorkOrder
from coactra.jobs.work import Artifact, ArtifactPart
from coactra.memory import Memory, Scope as MemoryScope, make_backend

WORK_SCOPE = WorkScope(tenant_id="acme", namespace="support-tickets")
AGENT_SCOPE = AgentScope(tenant_id="acme", namespace="agent:support")
MEMORY_SCOPE = MemoryScope(tenant="acme", namespace="support", agent="helpdesk")


def ticket_key(ticket_id: str) -> str:
    digest = hashlib.sha256(ticket_id.encode("utf-8")).hexdigest()[:12]
    return f"ticket:{digest}"


def build_memory() -> Memory:
    return Memory(backend=make_backend("inprocess"))


def remember_fix(memory: Memory, ticket_id: str, fix: str) -> None:
    memory.sync.remember([f"{ticket_id} fix={fix}"], scope=MEMORY_SCOPE)


def recall_fix(memory: Memory, issue: str) -> str | None:
    matches = memory.sync.recall(issue, scope=MEMORY_SCOPE, k=1)
    return matches[0].text if matches else None


def open_ticket(work: WorkManager, ticket_id: str, issue: str) -> WorkOrder:
    return work.submit(
        WorkOrder(
            scope=WORK_SCOPE,
            title=f"Resolve {ticket_id}: {issue[:72]}",
            idempotency_key=ticket_key(ticket_id),
        )
    )


def triage_ticket(
    ticket_id: str,
    issue: str,
    *,
    memory: Memory | None = None,
    work: WorkManager | None = None,
) -> dict[str, object]:
    memory = memory or build_memory()
    work = work or WorkManager()
    agent = make_agent(scope=AGENT_SCOPE)

    prior = recall_fix(memory, issue)
    draft = agent.think(f"Triage {ticket_id}: {issue}. Prior fix: {prior or 'none'}")

    order = open_ticket(work, ticket_id, issue)
    lease = work.claim(order.id, WORK_SCOPE, worker="agent:support", lease_seconds=120)
    work.start(lease, WORK_SCOPE)
    work.checkpoint(lease, WORK_SCOPE, {"draft": draft, "prior_fix": prior})
    completed = work.complete(
        lease,
        WORK_SCOPE,
        artifacts=[Artifact(name="triage-note", parts=[ArtifactPart(kind="text", text=draft)])],
    )
    remember_fix(memory, ticket_id, draft)

    return {
        "ticket_id": ticket_id,
        "work_id": completed.id,
        "status": completed.status.value,
        "prior_fix": prior,
        "draft": draft,
        "events": [event.type for event in work.events(completed.id, WORK_SCOPE)],
    }


def main() -> None:
    memory = build_memory()
    remember_fix(memory, "T-050", "rotate API key and restart billing worker")
    pprint(triage_ticket("T-1842", "API key worker failing after deploy", memory=memory))


if __name__ == "__main__":
    main()
