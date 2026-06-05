"""coactra.jobs - durable work orders plus reusable procedures."""

from coactra.jobs.facade import (
    DurableOrchestrationResult,
    DurableOrchestrator,
    OrchestrationResult,
    Orchestrator,
    ProcedureNotFoundError,
    WorkflowEngineRequiredError,
)
from coactra.jobs.work import (
    ExecutionPlan,
    ExecutionReceipt,
    WorkManager,
    WorkOrder,
)
from coactra.jobs.work.domain.scope import Scope as WorkScope
from coactra.jobs.workflow import (
    DurableLangGraphEngine,
    Capability,
    CapabilityRegistry,
    CapabilityValidationError,
    InMemoryCapabilityRegistry,
    Procedure,
    Step,
    ToolInvoker,
    VerificationResult,
    build_graph,
    check_done_criteria,
    document_from_procedure,
    run_workflow,
    verify_done_criteria,
)
from coactra.jobs.workflow.domain.scope import Scope as WorkflowScope

__all__ = [
    "__version__",
    "DurableOrchestrationResult",
    "DurableOrchestrator",
    "DurableLangGraphEngine",
    "Capability",
    "CapabilityRegistry",
    "CapabilityValidationError",
    "InMemoryCapabilityRegistry",
    "ToolInvoker",
    "VerificationResult",
    "ExecutionPlan",
    "ExecutionReceipt",
    "OrchestrationResult",
    "Orchestrator",
    "Procedure",
    "ProcedureNotFoundError",
    "Step",
    "build_graph",
    "run_workflow",
    "document_from_procedure",
    "check_done_criteria",
    "verify_done_criteria",
    "WorkflowEngineRequiredError",
    "WorkflowScope",
    "WorkManager",
    "WorkOrder",
    "WorkScope",
]

# Convenience aliases: work-order internals remain under ``coactra.jobs.work`` but
# adapter/backend imports are common enough to expose at the package root.
from importlib import import_module as _import_module
import sys as _sys

for _suffix in (
    "adapters",
    "adapters._optional",
    "adapters.a2a",
    "adapters.cloudevents",
    "adapters.dapr",
    "adapters.dbos",
    "adapters.fsspec",
    "adapters.mcp_tasks",
    "adapters.opentelemetry",
    "adapters.temporal",
    "backends",
    "backends.inmemory",
    "backends.sql",
    "conformance",
    "domain",
    "domain.artifacts",
    "domain.capabilities",
    "domain.events",
    "domain.models",
    "domain.plans",
    "domain.scope",
    "service",
    "store",
    "routing",
):
    _sys.modules[f"{__name__}.{_suffix}"] = _import_module(
        f"coactra.jobs.work.{_suffix}"
    )

# Expose the work-order vocabulary at the jobs root. This keeps the common import
# path short: ``from coactra.jobs import Scope, WorkManager, WorkOrder``.
from coactra.jobs import work as _work_module

for _name in _work_module.__all__:
    if _name != "__version__":
        globals().setdefault(_name, getattr(_work_module, _name))

__all__ = sorted(set(__all__) | {
    _name for _name in _work_module.__all__ if _name != "__version__"
})

__version__ = "0.1.0"
