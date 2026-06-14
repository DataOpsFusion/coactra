"""Ticket triage with Team, Memory, and durable work."""

from __future__ import annotations

import asyncio
import hashlib
from pprint import pprint

from pydantic_ai.messages import ModelResponse, TextPart
from pydantic_ai.models.function import AgentInfo, FunctionModel

from coactra import ModelProfile, ModelResolver, ModelRoute, Policy, Scope, Skill, Team
from coactra.memory import Memory, Scope as MemoryScope, make_backend
from coactra.workflow.ledger import Artifact, ArtifactPart, WorkManager, WorkOrder
from coactra.workflow.ledger.domain.scope import Scope as WorkScope

WORK_SCOPE = WorkScope(tenant_id="acme", namespace="support-tickets")
MEMORY_SCOPE = MemoryScope(tenant="acme", namespace="support", agent="helpdesk")


def ticket_key(ticket_id: str) -> str:
    digest = hashlib.sha256(ticket_id.encode("utf-8")).hexdigest()[:12]
    return f"ticket:{digest}"


def triage_model(messages, info: AgentInfo) -> ModelResponse:  # noqa: ARG001
    return ModelResponse(parts=[TextPart("Rotate the API key, restart the worker, and verify auth logs.")])


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


async def triage_ticket(
    ticket_id: str,
    issue: str,
    *,
    memory: Memory | None = None,
    work: WorkManager | None = None,
) -> dict[str, object]:
    memory = memory or build_memory()
    work = work or WorkManager()
    team = Team(
        scope=Scope(tenant_id="acme", namespace="support"),
        policy=Policy.permissive(),
        model_resolver=ModelResolver([
            ModelRoute(capability="support-triage", profile=ModelProfile(name="support-triage", model=FunctionModel(triage_model)))
        ]),
    )
    agent = await team.add_agent(
        model_capability="support-triage",
        name="helpdesk-agent",
        auth="dev-token",
        skills=[Skill(id="support.triage", description="Triage support tickets")],
        expose=True,
    )

    prior = recall_fix(memory, issue)
    prior_text = prior or "none"
    draft = await agent.run(f"Triage {ticket_id}: {issue}. Prior fix: {prior_text}")

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


async def main() -> None:
    memory = build_memory()
    remember_fix(memory, "T-050", "rotate API key and restart billing worker")
    pprint(await triage_ticket("T-1842", "API key worker failing after deploy", memory=memory))


if __name__ == "__main__":
    asyncio.run(main())
