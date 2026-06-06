from types import SimpleNamespace

import pytest

from coactra.jobs.workflow import (
    Scope,
    WorkflowEngine,
    WorkflowRunStatus,
    make_workflow_engine,
)
from coactra.jobs.workflow.adapters.prefect import PrefectEngine
from coactra.jobs.workflow.adapters.temporal import TemporalEngine
from coactra.jobs.workflow.conformance import assert_workflow_engine_start_contract
from coactra.jobs.workflow.runtime import RunContext
from coactra.jobs.workflow.domain.models import Procedure, Step


def procedure():
    return Procedure(name="demo", steps=[Step(id="start", kind="task")])


def ctx():
    return RunContext(scope=Scope(tenant_id="acme", namespace="ops"))


class TemporalHandle:
    def __init__(self, workflow_id="thread-1", result_value=None):
        self.id = workflow_id
        self.run_id = "run-1"
        self.result_value = result_value or {
            "status": "completed",
            "result": {"output": {"done": True}, "path": ["start"]},
            "state": {"done": True},
        }
        self.signals = []

    async def result(self):
        return self.result_value

    async def signal(self, name, payload, **kwargs):
        self.signals.append((name, payload, kwargs))


class TemporalClient:
    def __init__(self):
        self.handle = TemporalHandle()
        self.started = []

    async def start_workflow(self, workflow, payload, **kwargs):
        self.started.append({"workflow": workflow, "payload": payload, "kwargs": kwargs})
        self.handle.id = kwargs["id"]
        return self.handle

    def get_workflow_handle(self, workflow_id):
        self.handle.id = workflow_id
        return self.handle


def test_adapters_name_the_engine_seam_they_satisfy():
    assert TemporalEngine.satisfies == "WorkflowEngine"
    assert PrefectEngine.satisfies == "WorkflowEngine"
    assert TemporalEngine.resume_semantics == "same-thread"
    assert PrefectEngine.resume_semantics == "new-run-with-prior-state"


@pytest.mark.asyncio
async def test_temporal_engine_starts_and_signals_same_thread():
    client = TemporalClient()
    engine = TemporalEngine(client=client, workflow="CoactraWorkflow", task_queue="coactra")

    run = await engine.start(procedure(), {"x": 1}, ctx(), thread_id="thread-1")
    resumed = await engine.resume(
        "thread-1",
        ctx(),
        procedure=procedure(),
        decision={"approved": True},
    )

    assert isinstance(engine, WorkflowEngine)
    assert run.status is WorkflowRunStatus.running
    assert run.thread_id == "thread-1"
    assert client.started[0]["workflow"] == "CoactraWorkflow"
    assert client.started[0]["kwargs"]["id"] == "thread-1"
    assert client.started[0]["kwargs"]["task_queue"] == "coactra"
    assert client.started[0]["payload"]["procedure"]["name"] == "demo"
    assert client.started[0]["payload"]["scope"] == {
        "tenant_id": "acme",
        "namespace": "ops",
    }
    assert resumed.status is WorkflowRunStatus.running
    assert client.handle.signals[0][0] == "resume"
    assert client.handle.signals[0][1]["decision"] == {"approved": True}


@pytest.mark.asyncio
async def test_temporal_engine_can_wait_for_result_and_normalize_dict():
    client = TemporalClient()
    engine = TemporalEngine(
        client=client,
        workflow="CoactraWorkflow",
        task_queue="coactra",
        wait_for_result=True,
    )

    run = await engine.start(procedure(), {}, ctx(), thread_id="thread-2")

    assert run.status is WorkflowRunStatus.completed
    assert run.result.output == {"done": True}
    assert run.result.path == ["start"]


class PrefectState:
    def __init__(self, *, completed=False, failed=False):
        self._completed = completed
        self._failed = failed

    def is_completed(self):
        return self._completed

    def is_failed(self):
        return self._failed


@pytest.mark.asyncio
async def test_prefect_engine_starts_and_resumes_as_new_deployment_runs():
    calls = []

    async def fake_run_deployment(**kwargs):
        calls.append(kwargs)
        return SimpleNamespace(id=f"flow-run-{len(calls)}", state=PrefectState())

    engine = PrefectEngine(
        deployment_name="coactra/run-procedure",
        run_deployment=fake_run_deployment,
        tags=["coactra"],
    )

    run = await engine.start(procedure(), {"x": 1}, ctx(), thread_id="thread-1")
    resumed = await engine.resume(
        "thread-1",
        ctx(),
        procedure=procedure(),
        decision={"approved": True},
        state={"x": 2},
    )

    assert isinstance(engine, WorkflowEngine)
    assert run.status is WorkflowRunStatus.running
    assert run.thread_id == "thread-1"
    assert run.state["prefect_flow_run_id"] == "flow-run-1"
    assert calls[0]["name"] == "coactra/run-procedure"
    assert calls[0]["parameters"]["coactra_action"] == "start"
    assert calls[0]["parameters"]["state"] == {"x": 1}
    assert calls[0]["idempotency_key"] == "thread-1"
    assert resumed.status is WorkflowRunStatus.running
    assert resumed.state["prefect_flow_run_id"] == "flow-run-2"
    assert calls[1]["parameters"]["coactra_action"] == "resume"
    assert calls[1]["parameters"]["coactra_resume_thread_id"] == "thread-1"
    assert calls[1]["parameters"]["decision"] == {"approved": True}
    assert "idempotency_key" not in calls[1]


@pytest.mark.asyncio
async def test_prefect_engine_normalizes_completed_flow_run():
    async def fake_run_deployment(**kwargs):
        return SimpleNamespace(id="flow-run-complete", state=PrefectState(completed=True))

    engine = PrefectEngine(
        deployment_name="coactra/run-procedure",
        run_deployment=fake_run_deployment,
    )

    run = await engine.start(procedure(), {}, ctx(), thread_id="thread-done")

    assert run.status is WorkflowRunStatus.completed
    assert run.result.output["prefect_flow_run_id"] == "flow-run-complete"


@pytest.mark.asyncio
async def test_external_engines_satisfy_start_conformance():
    temporal = TemporalEngine(client=TemporalClient(), workflow="W", task_queue="q")

    async def fake_run_deployment(**kwargs):
        return SimpleNamespace(id="flow-run", state=PrefectState())

    prefect = PrefectEngine(
        deployment_name="flow/deploy",
        run_deployment=fake_run_deployment,
    )

    await assert_workflow_engine_start_contract(temporal)
    await assert_workflow_engine_start_contract(prefect)


def test_make_workflow_engine_can_build_temporal_and_prefect_adapters():
    temporal = make_workflow_engine(
        "temporal",
        client=TemporalClient(),
        workflow="CoactraWorkflow",
        task_queue="coactra",
    )
    prefect = make_workflow_engine(
        "prefect",
        deployment_name="coactra/run-procedure",
        run_deployment=lambda **kwargs: {"status": "running"},
    )

    assert isinstance(temporal, TemporalEngine)
    assert isinstance(prefect, PrefectEngine)
