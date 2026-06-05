"""Reusable conformance checks for ``WorkflowEngine`` implementations."""
from __future__ import annotations

from coactra.jobs.workflow.domain.models import Procedure, Step
from coactra.jobs.workflow.domain.scope import Scope
from coactra.jobs.workflow.runtime import RunContext, WorkflowEngine, WorkflowRun


def sample_procedure() -> Procedure:
    return Procedure(name="conformance", steps=[Step(id="start", kind="task")])


def sample_context() -> RunContext:
    return RunContext(scope=Scope(tenant_id="conformance", namespace="workflow"))


async def assert_workflow_engine_start_contract(engine: WorkflowEngine) -> WorkflowRun:
    """Assert that an engine can start a run and return a serializable snapshot."""

    run = await engine.start(
        sample_procedure(),
        {"input": "ok"},
        sample_context(),
        thread_id="conformance-thread",
    )
    assert isinstance(run, WorkflowRun)
    assert run.thread_id
    assert run.status.value in {"running", "interrupted", "completed", "failed"}
    return run
