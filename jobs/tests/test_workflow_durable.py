import pytest

from coactra.jobs.workflow import (
    AsyncProcedureRunnerAdapter,
    InMemoryApprovalStore,
    PendingApproval,
    Procedure,
    RunContext,
    RunResult,
    Scope,
    Step,
    WorkflowEngine,
    WorkflowNotResumableError,
    WorkflowRunStatus,
    make_workflow_engine,
)


class Runner:
    def run(self, procedure, state, ctx):
        return RunResult(output={**state, "done": True}, path=[procedure.entry.id])


@pytest.mark.asyncio
async def test_async_adapter_exposes_start_with_stable_thread_id_without_fake_resume():
    engine = AsyncProcedureRunnerAdapter(Runner())
    assert isinstance(engine, WorkflowEngine)
    ctx = RunContext(scope=Scope(tenant_id="acme"))
    procedure = Procedure(name="x", steps=[Step(id="a", kind="task")])

    first = await engine.start(procedure, {"v": 1}, ctx, thread_id="thread-1")
    second = await engine.start(procedure, {"v": 999}, ctx, thread_id="thread-1")

    assert first == second
    assert first.status is WorkflowRunStatus.completed
    assert first.result.output == {"v": 1, "done": True}
    with pytest.raises(WorkflowNotResumableError):
        await engine.resume("thread-1", ctx)


def test_pending_approval_store_is_scope_isolated_and_decidable():
    acme = Scope(tenant_id="acme")
    globex = Scope(tenant_id="globex")
    store = InMemoryApprovalStore()
    approval = store.save(PendingApproval(thread_id="t-1", step_id="review", scope=acme, prompt="Ship?"))

    assert store.get(approval.id, globex) is None
    assert [item.id for item in store.pending(acme)] == [approval.id]
    decided = store.decide(approval.id, acme, approved=True, decided_by="human:ops")
    assert decided.status == "approved"
    assert decided.decided_by == "human:ops"
    assert store.pending(acme) == []

def test_make_workflow_engine_local_runtime_wraps_runner_without_fake_resume():
    engine = make_workflow_engine("local", runner=Runner())

    assert isinstance(engine, WorkflowEngine)


def test_make_workflow_engine_rejects_unknown_runtime():
    with pytest.raises(ValueError, match="unknown workflow runtime"):
        make_workflow_engine("unknown")  # type: ignore[arg-type]


def test_make_default_workflow_engine_names_langgraph_as_default(monkeypatch):
    calls = []

    class FakeDurableLangGraphEngine:
        pass

    def fake_make(runtime="default", **kwargs):
        calls.append((runtime, kwargs))
        return FakeDurableLangGraphEngine()

    import coactra.jobs.workflow.runtime.defaults as defaults

    monkeypatch.setattr(defaults, "make_workflow_engine", fake_make)

    assert isinstance(defaults.make_default_workflow_engine(answer=42), FakeDurableLangGraphEngine)
    assert calls == [("langgraph", {"answer": 42})]
