"""Procedure-backed work: register a recipe, submit a work order, run via Orchestrator."""

from __future__ import annotations

from pprint import pprint

from coactra.jobs import Orchestrator, Procedure, Step, WorkOrder, WorkScope
from coactra.jobs.workflow import RunResult


SCOPE = WorkScope(tenant_id="acme", namespace="support")


class InspectEngine:
    """Minimal in-process procedure runner for demos and tests."""

    def run(self, procedure, state, ctx):
        path = [step.id for step in procedure.steps]
        return RunResult(output={**state, "procedure": procedure.name}, path=path)


def register_incident_procedure(orchestrator: Orchestrator) -> None:
    orchestrator.register(
        Procedure(
            name="incident",
            steps=[
                Step(id="triage", kind="task"),
                Step(id="notify", kind="task"),
            ],
        ),
        SCOPE,
    )


def submit_incident(orchestrator: Orchestrator, incident_id: str) -> WorkOrder:
    return orchestrator.submit(
        WorkOrder(
            scope=SCOPE,
            title=f"Investigate {incident_id}",
            procedure="incident",
        )
    )


def run_incident(orchestrator: Orchestrator, incident_id: str) -> dict[str, object]:
    register_incident_procedure(orchestrator)
    order = submit_incident(orchestrator, incident_id)
    result = orchestrator.run(
        order.id,
        SCOPE,
        worker="agent:platform",
        state={"incident": incident_id},
    )
    return {
        "work_id": result.order.id,
        "status": result.order.status.value,
        "procedure": result.run.output.get("procedure"),
        "path": result.run.path,
    }


def main() -> None:
    orchestrator = Orchestrator(engine=InspectEngine())
    pprint(run_incident(orchestrator, "INC-4821"))


if __name__ == "__main__":
    main()
