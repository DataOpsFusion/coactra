"""Durable release runner sample.

Shows WorkManager as a lifecycle ledger for real work: submit, claim, start,
checkpoint, complete, and audit events.
"""

from __future__ import annotations

import hashlib
from pprint import pprint

from coactra.jobs import (
    Artifact,
    ArtifactPart,
    WorkManager,
    WorkOrder,
    WorkScope,
)

WORK_SCOPE = WorkScope(tenant_id="acme", namespace="release")


def release_key(version: str) -> str:
    digest = hashlib.sha256(version.encode("utf-8")).hexdigest()[:16]
    return f"release:{digest}"


def submit_release(work: WorkManager, version: str) -> WorkOrder:
    return work.submit(
        WorkOrder(
            scope=WORK_SCOPE,
            title=f"Ship version {version}",
            idempotency_key=release_key(version),
        )
    )


def run_release(work: WorkManager, version: str) -> dict[str, object]:
    order = submit_release(work, version)
    lease = work.claim(order.id, WORK_SCOPE, worker="agent:release", lease_seconds=300)
    work.start(lease, WORK_SCOPE)
    work.checkpoint(lease, WORK_SCOPE, {"step": "tests-passed"})

    artifact = Artifact(
        name="release-notes",
        parts=[ArtifactPart(kind="text", text=f"Release {version} shipped.")],
    )
    completed = work.complete(lease, WORK_SCOPE, artifacts=[artifact])

    return {
        "work_id": completed.id,
        "status": completed.status.value,
        "artifact_names": [item.name for item in completed.artifacts],
        "events": [event.type for event in work.events(completed.id, WORK_SCOPE)],
    }


def main() -> None:
    pprint(run_release(WorkManager(), "2026.06.04"))


if __name__ == "__main__":
    main()
