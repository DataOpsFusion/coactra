"""Support ticket agent using the current Agent facade.

The model is local and deterministic so the script runs in CI and fresh checkouts
with `coactra[agent]` installed.
"""

from __future__ import annotations

import asyncio
import hashlib
from pprint import pprint

from pydantic_ai.messages import ModelResponse, TextPart
from pydantic_ai.models.function import AgentInfo, FunctionModel

from coactra import Agent, Skill
from coactra.workflow import WorkScope, WorkManager, WorkOrder

WORK_SCOPE = WorkScope(tenant_id="acme", namespace="support-tickets")


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
    agent = await Agent.create(
        model=FunctionModel(ticket_model),
        name="support-agent",
        tenant="acme",
        auth="dev-token",
        tools=[fetch_ticket],
        skills=[Skill(id="support.triage", description="Triage support tickets")],
        instructions="Draft concise support triage notes.",
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
