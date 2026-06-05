"""Minimal work-order lifecycle: submit → claim → start → checkpoint → complete."""

from __future__ import annotations

from pprint import pprint

from coactra.jobs import (
    Artifact,
    ArtifactPart,
    Scope,
    WorkManager,
    WorkOrder,
)

SCOPE = Scope(tenant_id="acme", namespace="ops")


def submit_report_work(work: WorkManager, title: str) -> WorkOrder:
    return work.submit(WorkOrder(scope=SCOPE, title=title))


def run_report(work: WorkManager, title: str) -> dict[str, object]:
    order = submit_report_work(work, title)
    lease = work.claim(order.id, SCOPE, worker="agent:analyst", lease_seconds=120)
    work.start(lease, SCOPE)
    work.checkpoint(lease, SCOPE, {"section": "summary"})

    artifact = Artifact(
        name="weekly-report",
        parts=[ArtifactPart(kind="text", text=f"Report: {title}")],
    )
    completed = work.complete(lease, SCOPE, artifacts=[artifact])

    return {
        "work_id": completed.id,
        "status": completed.status.value,
        "artifacts": [item.name for item in completed.artifacts],
        "events": [event.type for event in work.events(completed.id, SCOPE)],
    }


def main() -> None:
    pprint(run_report(WorkManager(), "Weekly platform summary"))


if __name__ == "__main__":
    main()
