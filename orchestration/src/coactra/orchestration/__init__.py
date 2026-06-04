"""coactra.orchestration - durable work orders plus reusable procedures."""

from coactra.orchestration.facade import (
    DurableOrchestrationResult,
    DurableOrchestrator,
    OrchestrationResult,
    Orchestrator,
    ProcedureNotFoundError,
    WorkflowEngineRequiredError,
)
from coactra.orchestration.work import (
    ExecutionPlan,
    ExecutionReceipt,
    WorkManager,
    WorkOrder,
)
from coactra.orchestration.work.domain.scope import Scope as WorkScope
from coactra.orchestration.workflow import (
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
from coactra.orchestration.workflow.domain.scope import Scope as WorkflowScope

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

__version__ = "0.1.0"
