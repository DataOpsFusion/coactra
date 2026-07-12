"""Support ticket agent using the Team-first facade."""

from __future__ import annotations

import asyncio
import hashlib
from pprint import pprint

from pydantic_ai.messages import ModelResponse, TextPart
from pydantic_ai.models.function import AgentInfo, FunctionModel

from coactra import ModelProfile, ModelResolver, ModelRoute, Policy, Scope, Skill, Team
from coactra.workflow.ledger import WorkManager, WorkOrder

WORK_SCOPE = Scope(tenant_id="acme", namespace="support-tickets")


def ticket_key(ticket_id: str) -> str:
    digest = hashlib.sha256(ticket_id.encode("utf-8")).hexdigest()[:12]
    return f"ticket:{digest}"


def ticket_model(messages, info: AgentInfo) -> ModelResponse:  # noqa: ARG001
    return ModelResponse(
        parts=[TextPart("Check auth headers, worker logs, and the most recent deploy.")]
    )


def fetch_ticket(ticket_id: str) -> dict[str, str]:
    return {"id": ticket_id, "status": "open", "subject": "billing worker rejects API key"}


def open_ticket(work: WorkManager, ticket_id: str, issue: str) -> WorkOrder:
    return work.submit(
        WorkOrder(
            scope=WORK_SCOPE,
            title=f"Resolve {ticket_id}: {issue[:64]}",
            idempotency_key=ticket_key(ticket_id),
        )
    )


async def handle_ticket(ticket_id: str, issue: str) -> dict[str, object]:
    work = WorkManager()
    team = Team(
        scope=Scope(tenant_id="acme", namespace="support"),
        policy=Policy.permissive(),
        model_resolver=ModelResolver([
            ModelRoute(capability="support-triage", profile=ModelProfile(name="support-triage", model=FunctionModel(ticket_model)))
        ]),
    )
    agent = await team.add_agent(
        model_capability="support-triage",
        name="support-agent",
        auth="dev-token",
        tools=[fetch_ticket],
        skills=[Skill(id="support.triage", description="Triage support tickets")],
        instructions="Draft concise support triage notes.",
        expose=True,
    )

    order = open_ticket(work, ticket_id, issue)
    draft = await agent.run(f"Issue: {issue}. Fetch ticket {ticket_id} and draft next steps.")

    return {
        "ticket_id": ticket_id,
        "work_id": order.id,
        "status": work.get(order.id, WORK_SCOPE).status.value,
        "draft": draft,
    }


async def main() -> None:
    pprint(await handle_ticket("T-1842", "billing worker rejects API key after deploy"))


if __name__ == "__main__":
    asyncio.run(main())
