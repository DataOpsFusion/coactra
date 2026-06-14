"""Run a registered procedure through an Orchestrator.

This uses a tiny in-process engine so the example is about the public contract,
not a specific workflow backend.
"""

from __future__ import annotations

from pprint import pprint

from coactra.workflow import Orchestrator, Procedure, Step
from coactra.workflow.ledger import WorkOrder
from coactra.workflow.ledger.domain.scope import Scope as WorkScope
from coactra.workflow import RunResult

SCOPE = WorkScope(tenant_id="acme", namespace="incident-response")


class InspectEngine:
    def run(self, procedure, state, ctx):  # noqa: ARG002
        return RunResult(
            output={**state, "procedure": procedure.name},
            path=[step.id for step in procedure.steps],
        )


def register_runbook(orchestrator: Orchestrator) -> None:
    orchestrator.register(
        Procedure(
            name="incident-handoff",
            steps=[
                Step(id="triage", kind="task"),
                Step(id="notify-owner", kind="task"),
                Step(id="write-handoff", kind="task"),
            ],
        ),
        SCOPE,
    )


def run_incident_runbook(orchestrator: Orchestrator, incident_id: str) -> dict[str, object]:
    register_runbook(orchestrator)
    order = orchestrator.submit(
        WorkOrder(scope=SCOPE, title=f"Investigate {incident_id}", procedure="incident-handoff")
    )
    result = orchestrator.run(
        order.id,
        SCOPE,
        worker="agent:oncall",
        state={"incident_id": incident_id},
    )
    return {
        "work_id": result.order.id,
        "status": result.order.status.value,
        "procedure": result.run.output["procedure"],
        "path": result.run.path,
    }


def main() -> None:
    pprint(run_incident_runbook(Orchestrator(engine=InspectEngine()), "INC-4821"))


if __name__ == "__main__":
    main()
