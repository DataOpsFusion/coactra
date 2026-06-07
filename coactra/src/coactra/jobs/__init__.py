"""coactra.jobs — durable work orders and reusable procedures."""

from __future__ import annotations

from coactra._version import distribution_version
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
from coactra.workflow import (
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
from coactra.workflow.domain.scope import Scope as WorkflowScope

Scope = WorkScope

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
    "Scope",
    "WorkflowScope",
    "WorkManager",
    "WorkOrder",
    "WorkScope",
]

__version__ = distribution_version()
