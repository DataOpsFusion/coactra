"""Incident response handoff using the current Agent facade.

This example runs offline with pydantic-ai FunctionModel and keeps durable work
state in the in-memory WorkManager.
"""

from __future__ import annotations

import asyncio
import hashlib
from pprint import pprint

from pydantic_ai.messages import ModelResponse, TextPart
from pydantic_ai.models.function import AgentInfo, FunctionModel

from coactra import Agent
from coactra.workflow.ledger import WorkManager, WorkOrder
from coactra.workflow.ledger.domain.scope import Scope as WorkScope
from coactra.workflow.ledger import Artifact, ArtifactPart

WORK_SCOPE = WorkScope(tenant_id="acme", namespace="incident-response")


def incident_key(summary: str) -> str:
    digest = hashlib.sha256(summary.encode("utf-8")).hexdigest()[:12]
    return f"incident:{digest}"


def open_incident(work: WorkManager, summary: str) -> WorkOrder:
    return work.submit(
        WorkOrder(
            scope=WORK_SCOPE,
            title=f"Triage incident: {summary[:72]}",
            idempotency_key=incident_key(summary),
        )
    )


def handoff_model(messages, info: AgentInfo) -> ModelResponse:  # noqa: ARG001
    return ModelResponse(
        parts=[TextPart("Likely deploy regression. Check error budget, rollback criteria, and DB saturation.")]
    )


async def handoff_incident(summary: str) -> dict[str, object]:
    work = WorkManager()
    agent = await Agent.create(
        model=FunctionModel(handoff_model),
        name="oncall-agent",
        tenant="acme",
        auth="dev-token",
        instructions="Draft concise on-call handoffs.",
    )

    order = open_incident(work, summary)
    draft = await agent.run(
        "Draft a short on-call handoff with likely cause, first check, and owner: "
        f"{summary}"
    )

    lease = work.claim(order.id, WORK_SCOPE, worker="agent:oncall", lease_seconds=120)
    work.start(lease, WORK_SCOPE)
    work.checkpoint(lease, WORK_SCOPE, {"draft_handoff": draft})
    completed = work.complete(
        lease,
        WORK_SCOPE,
        artifacts=[Artifact(name="on-call-handoff", parts=[ArtifactPart(kind="text", text=draft)])],
    )

    return {
        "work_id": completed.id,
        "status": completed.status.value,
        "handoff": draft,
        "events": [event.type for event in work.events(completed.id, WORK_SCOPE)],
    }


if __name__ == "__main__":
    pprint(asyncio.run(handoff_incident("checkout latency spiked after the 14:05 deploy")))
