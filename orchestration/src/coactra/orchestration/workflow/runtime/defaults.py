"""Default durable workflow runtime selection.

Coactra owns the stable ``WorkflowEngine`` boundary. LangGraph is the default
agentic runtime when installed; Temporal and Prefect are explicit named adapters
for harder durable-execution deployments.
"""
from __future__ import annotations

from typing import Any, Literal

from coactra.orchestration.workflow.runtime.durable import (
    AsyncProcedureRunnerAdapter,
    WorkflowEngine,
)
from coactra.orchestration.workflow.runtime.engine import ProcedureRunner

WorkflowRuntime = Literal["default", "langgraph", "local", "temporal", "prefect"]


def make_default_workflow_engine(**kwargs: Any) -> WorkflowEngine:
    """Build the default durable workflow engine.

    The default is the checkpointed LangGraph adapter because Coactra workflows
    are agent/tool/human-interrupt shaped. Install ``coactra-orchestration[langgraph]``
    for this path, or inject another ``WorkflowEngine`` explicitly.
    """

    return make_workflow_engine("langgraph", **kwargs)


def make_workflow_engine(
    runtime: WorkflowRuntime = "default",
    *,
    runner: ProcedureRunner | None = None,
    **kwargs: Any,
) -> WorkflowEngine:
    """Build a workflow engine behind Coactra's ``WorkflowEngine`` Protocol.

    ``runtime="default"`` and ``runtime="langgraph"`` both use
    ``DurableLangGraphEngine``. ``runtime="local"`` is a test/prototype bridge
    over a synchronous ``ProcedureRunner`` and deliberately rejects resume.
    ``temporal`` and ``prefect`` route through thin external runtime adapters.
    """

    selected = "langgraph" if runtime == "default" else runtime
    if selected == "langgraph":
        try:
            from coactra.orchestration.workflow.backends.durable_langgraph import (
                DurableLangGraphEngine,
            )
        except ImportError as exc:  # pragma: no cover - depends on optional extra
            raise ImportError(
                "the default workflow runtime requires coactra-orchestration[langgraph]; "
                "install that extra or inject a WorkflowEngine explicitly"
            ) from exc
        return DurableLangGraphEngine(**kwargs)

    if selected == "local":
        if runner is None:
            raise ValueError('runtime="local" requires runner=...')
        if kwargs:
            names = ", ".join(sorted(kwargs))
            raise TypeError(f'unsupported local runtime options: {names}')
        return AsyncProcedureRunnerAdapter(runner)

    if selected == "temporal":
        from coactra.orchestration.workflow.adapters.temporal import TemporalEngine

        return TemporalEngine(**kwargs)

    if selected == "prefect":
        from coactra.orchestration.workflow.adapters.prefect import PrefectEngine

        return PrefectEngine(**kwargs)

    raise ValueError(f"unknown workflow runtime: {runtime!r}")
