import pytest

from coactra.orchestration import (
    DurableOrchestrator,
    Procedure,
    Step,
    WorkOrder,
    WorkScope,
)
from coactra.orchestration.workflow import (
    WorkflowInterrupt,
    WorkflowRun,
    WorkflowRunStatus,
)


class Engine:
    def __init__(self):
        self.resumed_procedure = None
        self.resumed_decision = None

    async def start(self, procedure, state, ctx, *, thread_id=None):
        return WorkflowRun(
            thread_id=thread_id or "thread-1",
            status=WorkflowRunStatus.interrupted,
            interrupt=WorkflowInterrupt(
                kind="approval", step_id="review", prompt="Ship?"
            ),
            state={**state, "built": True},
        )

    async def resume(
        self, thread_id, ctx, *, procedure=None, decision=None, state=None
    ):
        self.resumed_procedure = procedure
        self.resumed_decision = decision
        return WorkflowRun(
            thread_id=thread_id,
            status=WorkflowRunStatus.completed,
            state={"shipped": True},
        )


@pytest.mark.asyncio
async def test_durable_orchestrator_checkpoints_interrupt_resolves_approval_and_resumes():
    scope = WorkScope(tenant_id="acme")
    engine = Engine()
    orchestrator = DurableOrchestrator(engine)
    orchestrator.register(
        Procedure(name="deploy", steps=[Step(id="review", kind="approve")]), scope
    )
    order = orchestrator.submit(
        WorkOrder(scope=scope, title="deploy", procedure="deploy")
    )

    interrupted = await orchestrator.start(
        order.id, scope, worker="agent:builder", state={"sha": "abc"}
    )
    assert interrupted.order.status == "blocked"
    assert interrupted.order.checkpoint.state["workflow_thread_id"] == "thread-1"
    assert interrupted.approval.prompt == "Ship?"

    queued = orchestrator.resolve_approval(
        order.id, scope, approved=True, decided_by="human:ops"
    )
    assert queued.status == "queued"
    completed = await orchestrator.resume(order.id, scope, worker="agent:builder")
    assert completed.order.status == "completed"
    assert engine.resumed_procedure.name == "deploy"
    assert engine.resumed_decision == {"approved": True}


@pytest.mark.asyncio
async def test_durable_orchestrator_does_not_resume_rejected_approval():
    scope = WorkScope(tenant_id="acme")
    engine = Engine()
    orchestrator = DurableOrchestrator(engine)
    orchestrator.register(
        Procedure(name="deploy", steps=[Step(id="review", kind="approve")]), scope
    )
    order = orchestrator.submit(
        WorkOrder(scope=scope, title="deploy", procedure="deploy")
    )
    await orchestrator.start(order.id, scope, worker="agent:builder")

    failed = orchestrator.resolve_approval(
        order.id, scope, approved=False, decided_by="human:ops"
    )

    assert failed.status == "failed"
    with pytest.raises(ValueError, match="resolve an interrupted approval"):
        await orchestrator.resume(order.id, scope, worker="agent:builder")
    assert engine.resumed_procedure is None

def test_durable_orchestrator_uses_default_workflow_engine_when_not_injected(monkeypatch):
    import coactra.orchestration.facade as facade

    built = []

    def fake_default_engine():
        built.append(True)
        return Engine()

    monkeypatch.setattr(facade, "make_default_workflow_engine", fake_default_engine)

    orchestrator = DurableOrchestrator()

    assert isinstance(orchestrator.engine, Engine)
    assert built == [True]
