
from coactra.workflow import (
    AsyncProcedureRunnerAdapter,
    AutoApprove,
    NullCollaborator,
    Procedure,
    ProcedureRunner,
    RunResult,
    Scope,
    Step,
    TerminalHumanRouter,
    WorkflowEngine,
)
from coactra.workflow.engine import RunContext


def _ctx():
    return RunContext(
        scope=Scope(tenant_id="acme"),
        approver=AutoApprove(),
        collaborator=NullCollaborator(),
        router=TerminalHumanRouter(),
        chain=["human"],
    )


class _Dummy:
    def run(self, procedure, state, ctx):
        return RunResult(output=state, path=[s.id for s in procedure.steps])


def test_local_runner_protocol_is_runtime_checkable():
    assert isinstance(_Dummy(), ProcedureRunner)


def test_durable_engine_requires_async_start_and_resume():
    assert not isinstance(_Dummy(), WorkflowEngine)
    assert isinstance(AsyncProcedureRunnerAdapter(_Dummy()), WorkflowEngine)


def test_run_context_defaults_are_filled_in():
    ctx = RunContext(scope=Scope(tenant_id="acme"))
    assert isinstance(ctx.approver, AutoApprove)
    assert isinstance(ctx.router, TerminalHumanRouter)
    assert ctx.chain == []


def test_dummy_runner_runs_via_context():
    p = Procedure(name="x", steps=[Step(id="a", kind="task")])
    out = _Dummy().run(p, {"v": 1}, _ctx())
    assert out.path == ["a"]
