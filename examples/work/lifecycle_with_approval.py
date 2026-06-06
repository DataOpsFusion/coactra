"""Work order with checkpoint, approval gate, resume, and completion."""

from __future__ import annotations

from pprint import pprint

from coactra.jobs import (
    Artifact,
    ArtifactPart,
    Decision,
    DecisionOutcome,
    Scope,
    WorkManager,
    WorkOrder,
    WorkStatus,
)

SCOPE = Scope(tenant_id="acme", namespace="support")


def submit_publish_work(work: WorkManager, title: str) -> WorkOrder:
    return work.submit(WorkOrder(scope=SCOPE, title=title))


def run_publish_with_approval(work: WorkManager, title: str) -> dict[str, object]:
    order = submit_publish_work(work, title)
    lease = work.claim(order.id, SCOPE, worker="agent:editor")
    work.start(lease, SCOPE)
    work.checkpoint(lease, SCOPE, {"draft": "ready for review"})

    request = work.request_approval(lease, SCOPE, prompt="Publish this report?")
    blocked = work.get(order.id, SCOPE)
    assert blocked.status == WorkStatus.blocked
    assert blocked.lease is None

    work.decide(
        order.id,
        SCOPE,
        Decision(
            request_id=request.id,
            outcome=DecisionOutcome.accepted,
            decided_by="human:owner",
        ),
    )
    lease = work.claim(order.id, SCOPE, worker="agent:editor")
    work.start(lease, SCOPE)

    artifact = Artifact(
        name="published-report",
        parts=[ArtifactPart(kind="text", text=title)],
    )
    completed = work.complete(lease, SCOPE, artifacts=[artifact])

    return {
        "work_id": completed.id,
        "status": completed.status.value,
        "approval_prompt": request.prompt,
        "events": [event.type for event in work.events(completed.id, SCOPE)],
    }


def main() -> None:
    pprint(run_publish_with_approval(WorkManager(), "Customer outage postmortem"))


if __name__ == "__main__":
    main()
