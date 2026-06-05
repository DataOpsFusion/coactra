"""Basic incident-triage app using normal Coactra imports.

This is the docs-first example: plain functions, no subclassing, no custom adapter
classes. It uses dependency-light defaults so it can run locally.
"""

from __future__ import annotations

import hashlib
from pprint import pprint

from coactra.agent import Scope as AgentScope
from coactra.agent import make_agent
from coactra.jobs import Scope as WorkScope
from coactra.jobs import WorkManager, WorkOrder


def incident_key(incident: str) -> str:
    digest = hashlib.sha256(incident.encode("utf-8")).hexdigest()[:16]
    return f"incident:{digest}"


def submit_incident(work: WorkManager, scope: WorkScope, incident: str) -> WorkOrder:
    """Create one durable unit of work for an incident."""
    return work.submit(
        WorkOrder(
            scope=scope,
            title=f"Triage incident: {incident[:60]}",
            idempotency_key=incident_key(incident),
        )
    )


def draft_first_checks(agent, incident: str) -> str:
    """Ask the configured agent facade for first-pass triage guidance.

    NOTE: ``make_agent`` with no AI port wired in uses an in-process ``FakeAI`` that
    echoes the prompt, so this returns ``"completion:Give the first three checks..."``
    rather than real model output. Wire a real model (see docs/PRODUCTION.md) for a
    meaningful draft.
    """
    return agent.think(f"Give the first three checks for this incident: {incident}")


def triage_incident(incident: str) -> dict[str, str]:
    """Application behavior as a plain function."""
    agent = make_agent(scope=AgentScope(tenant_id="acme", namespace="agent:support"))
    work = WorkManager()
    work_scope = WorkScope(tenant_id="acme", namespace="support")

    order = submit_incident(work, work_scope, incident)
    draft = draft_first_checks(agent, incident)

    return {
        "work_id": order.id,
        "status": order.status.value,
        "draft": draft,
    }


if __name__ == "__main__":
    pprint(triage_incident("database latency is high after the deploy"))
