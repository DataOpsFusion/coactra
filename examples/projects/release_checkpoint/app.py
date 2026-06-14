"""Release checkpoint ledger using WorkManager.

Use WorkManager when a release has durable state: claim ownership, save
checkpoints, attach artifacts, and inspect audit events.
"""

from __future__ import annotations

import hashlib
from pprint import pprint

from coactra.workflow.ledger import WorkManager, WorkOrder
from coactra.workflow.ledger.domain.scope import Scope as WorkScope
from coactra.workflow.ledger import Artifact, ArtifactPart

SCOPE = WorkScope(tenant_id="acme", namespace="release")


def release_key(version: str) -> str:
    digest = hashlib.sha256(version.encode("utf-8")).hexdigest()[:12]
    return f"release:{digest}"


def open_release(work: WorkManager, version: str) -> WorkOrder:
    return work.submit(
        WorkOrder(
            scope=SCOPE,
            title=f"Ship coactra {version}",
            idempotency_key=release_key(version),
        )
    )


def ship_release(work: WorkManager, version: str) -> dict[str, object]:
    order = open_release(work, version)
    lease = work.claim(order.id, SCOPE, worker="agent:release", lease_seconds=300)
    work.start(lease, SCOPE)
    work.checkpoint(lease, SCOPE, {"step": "tests passed"})
    work.checkpoint(lease, SCOPE, {"step": "wheel built"})

    completed = work.complete(
        lease,
        SCOPE,
        artifacts=[
            Artifact(
                name="release-summary",
                parts=[ArtifactPart(kind="text", text=f"Release {version} shipped.")],
            )
        ],
    )

    return {
        "version": version,
        "work_id": completed.id,
        "status": completed.status.value,
        "events": [event.type for event in work.events(completed.id, SCOPE)],
    }


def main() -> None:
    pprint(ship_release(WorkManager(), "0.2.0"))


if __name__ == "__main__":
    main()
