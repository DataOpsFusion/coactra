"""Incident response handoff with the stable Coactra facades.

This is the smallest normal app example. It runs offline: WorkManager uses an
in-memory store, and make_agent uses the local fake AI port unless you inject a
real model adapter.
"""

from __future__ import annotations

import hashlib
from pprint import pprint

from coactra.agent import Scope as AgentScope, make_agent
from coactra.jobs import Scope as WorkScope, WorkManager, WorkOrder
from coactra.jobs.work import Artifact, ArtifactPart

WORK_SCOPE = WorkScope(tenant_id="acme", namespace="incident-response")
AGENT_SCOPE = AgentScope(tenant_id="acme", namespace="agent:oncall")


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


def handoff_incident(summary: str) -> dict[str, object]:
    work = WorkManager()
    agent = make_agent(scope=AGENT_SCOPE)

    order = open_incident(work, summary)
    draft = agent.think(
        "Draft a short on-call handoff with likely cause, first check, and owner: "
        f"{summary}"
    )

    lease = work.claim(order.id, WORK_SCOPE, worker="agent:oncall", lease_seconds=120)
    work.start(lease, WORK_SCOPE)
    work.checkpoint(lease, WORK_SCOPE, {"draft_handoff": draft})
    completed = work.complete(
        lease,
        WORK_SCOPE,
        artifacts=[
            Artifact(
                name="on-call-handoff",
                parts=[ArtifactPart(kind="text", text=draft)],
            )
        ],
    )

    return {
        "work_id": completed.id,
        "status": completed.status.value,
        "handoff": draft,
        "events": [event.type for event in work.events(completed.id, WORK_SCOPE)],
    }


if __name__ == "__main__":
    pprint(handoff_incident("checkout latency spiked after the 14:05 deploy"))
