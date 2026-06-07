"""Release work lifecycle: submit, claim, checkpoint, complete."""

from __future__ import annotations

from pprint import pprint

from coactra.workflow import WorkScope, WorkManager, WorkOrder
from coactra.workflow.ledger import Artifact, ArtifactPart

SCOPE = WorkScope(tenant_id="acme", namespace="release")


def run_release_checklist(work: WorkManager, version: str) -> dict[str, object]:
    order = work.submit(WorkOrder(scope=SCOPE, title=f"Release {version}"))
    lease = work.claim(order.id, SCOPE, worker="agent:release", lease_seconds=180)
    work.start(lease, SCOPE)
    work.checkpoint(lease, SCOPE, {"step": "tests passed"})
    work.checkpoint(lease, SCOPE, {"step": "twine check passed"})
    completed = work.complete(
        lease,
        SCOPE,
        artifacts=[Artifact(name="release-note", parts=[ArtifactPart(kind="text", text=version)])],
    )
    return {
        "work_id": completed.id,
        "status": completed.status.value,
        "events": [event.type for event in work.events(completed.id, SCOPE)],
    }


def main() -> None:
    pprint(run_release_checklist(WorkManager(), "0.2.0"))


if __name__ == "__main__":
    main()
