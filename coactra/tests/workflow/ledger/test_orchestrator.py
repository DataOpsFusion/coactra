from coactra.workflow import Orchestrator, Procedure, RunResult, Step
from coactra.workflow.ledger import WorkOrder
from coactra.workflow.ledger.domain.scope import Scope as WorkScope


class Engine:
    def run(self, procedure, state, ctx):
        return RunResult(output={**state, "procedure": procedure.name}, path=["inspect"])


def test_orchestrator_runs_registered_procedure_and_completes_work_order():
    scope = WorkScope(tenant_id="acme", namespace="support")
    orchestrator = Orchestrator(engine=Engine())
    orchestrator.register(
        Procedure(name="incident", steps=[Step(id="inspect", kind="task")]), scope
    )
    order = orchestrator.submit(
        WorkOrder(scope=scope, title="Investigate INC-4821", procedure="incident")
    )

    result = orchestrator.run(order.id, scope, worker="agent:platform", state={"incident": "4821"})

    assert result.order.status == "completed"
    assert result.run.output == {"incident": "4821", "procedure": "incident"}
    assert result.run.path == ["inspect"]
