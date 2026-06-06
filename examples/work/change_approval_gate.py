"""Pause a work order for human approval, then resume it."""

from __future__ import annotations

from pprint import pprint

from coactra.jobs import Scope, WorkManager, WorkOrder
from coactra.jobs.work import Artifact, ArtifactPart, Decision, DecisionOutcome, WorkStatus

SCOPE = Scope(tenant_id="acme", namespace="change-management")


def run_change_with_approval(work: WorkManager, change_id: str) -> dict[str, object]:
    order = work.submit(WorkOrder(scope=SCOPE, title=f"Approve change {change_id}"))
    lease = work.claim(order.id, SCOPE, worker="agent:release")
    work.start(lease, SCOPE)
    work.checkpoint(lease, SCOPE, {"change_id": change_id, "risk": "low"})

    request = work.request_approval(lease, SCOPE, prompt=f"Deploy {change_id} to production?")
    blocked = work.get(order.id, SCOPE)
    assert blocked.status == WorkStatus.blocked

    work.decide(
        order.id,
        SCOPE,
        Decision(
            request_id=request.id,
            outcome=DecisionOutcome.accepted,
            decided_by="human:release-owner",
        ),
    )
    lease = work.claim(order.id, SCOPE, worker="agent:release")
    work.start(lease, SCOPE)
    completed = work.complete(
        lease,
        SCOPE,
        artifacts=[Artifact(name="approval-record", parts=[ArtifactPart(kind="text", text=change_id)])],
    )
    return {
        "work_id": completed.id,
        "status": completed.status.value,
        "approval_prompt": request.prompt,
        "events": [event.type for event in work.events(completed.id, SCOPE)],
    }


def main() -> None:
    pprint(run_change_with_approval(WorkManager(), "CHG-2048"))


if __name__ == "__main__":
    main()
