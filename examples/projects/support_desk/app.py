"""Support desk sample — agent draft, durable work, and ticket memory together.

Runs offline with in-process fakes. Swap backends for production; keep plain
functions for application behavior.
"""

from __future__ import annotations

import hashlib
from pprint import pprint

from coactra.agent import Scope as AgentScope, make_agent
from coactra.jobs import (
    Artifact,
    ArtifactPart,
    Scope,
    WorkManager,
    WorkOrder,
)
from coactra.memory import Memory, Scope as MemoryScope, make_backend

WORK_SCOPE = Scope(tenant_id="acme", namespace="support")
AGENT_SCOPE = AgentScope(tenant_id="acme", namespace="agent:support")
MEMORY_SCOPE = MemoryScope(tenant="acme", namespace="support", agent="helpdesk")


def ticket_key(ticket_id: str) -> str:
    digest = hashlib.sha256(ticket_id.encode("utf-8")).hexdigest()[:16]
    return f"ticket:{digest}"


def build_memory() -> Memory:
    return Memory(backend=make_backend("inprocess"))


def remember_resolution(memory: Memory, ticket_id: str, customer: str, resolution: str) -> None:
    memory.sync.remember(
        [f"ticket {ticket_id}: customer={customer}; resolution={resolution}"],
        scope=MEMORY_SCOPE,
    )


def recall_prior_fix(memory: Memory, issue: str) -> str | None:
    hits = memory.sync.recall(issue, scope=MEMORY_SCOPE, k=1)
    return hits[0].text if hits else None


def draft_triage(agent, issue: str, prior: str | None) -> str:
    context = f" Prior fix: {prior}." if prior else ""
    return agent.think(f"First three checks for: {issue}.{context}")


def submit_ticket(work: WorkManager, ticket_id: str, issue: str) -> WorkOrder:
    return work.submit(
        WorkOrder(
            scope=WORK_SCOPE,
            title=f"Support ticket {ticket_id}: {issue[:60]}",
            idempotency_key=ticket_key(ticket_id),
        )
    )


def handle_ticket(
    ticket_id: str,
    customer: str,
    issue: str,
    *,
    memory: Memory | None = None,
    work: WorkManager | None = None,
) -> dict[str, object]:
    memory = memory or build_memory()
    work = work or WorkManager()
    agent = make_agent(scope=AGENT_SCOPE)

    prior = recall_prior_fix(memory, issue)
    draft = draft_triage(agent, issue, prior)
    order = submit_ticket(work, ticket_id, issue)

    lease = work.claim(order.id, WORK_SCOPE, worker="agent:support", lease_seconds=120)
    work.start(lease, WORK_SCOPE)
    work.checkpoint(lease, WORK_SCOPE, {"draft": draft, "prior_fix": prior})

    artifact = Artifact(
        name="triage-summary",
        parts=[ArtifactPart(kind="text", text=draft)],
    )
    completed = work.complete(lease, WORK_SCOPE, artifacts=[artifact])
    remember_resolution(memory, ticket_id, customer, draft)

    return {
        "ticket_id": ticket_id,
        "work_id": completed.id,
        "status": completed.status.value,
        "prior_fix": prior,
        "draft": draft,
        "artifacts": [item.name for item in completed.artifacts],
        "events": [event.type for event in work.events(completed.id, WORK_SCOPE)],
    }


def main() -> None:
    memory = build_memory()
    remember_resolution(
        memory,
        "T-050",
        "Globex",
        "rotate API key and restart worker",
    )
    pprint(
        handle_ticket(
            "T-100",
            "Initech",
            "API key worker failing after deploy",
            memory=memory,
        )
    )


if __name__ == "__main__":
    main()
