"""coactra.workflow — public playbooks plus durable Procedure engines.

Workflow owns the definition and run ledger: authored flows, induced procedures,
approvals, checkpoints, and runtime adapters. Team/directory policy decides who may act;
agent transports carry the talk. Induction is trace-faithful and deterministic; update()
is manual so the library does not overclaim self-learning.
"""

from importlib import import_module
from typing import Any

from coactra._version import distribution_version
from coactra.workflow.playbook import (
    Approval,
    Playbook,
    Step as PlaybookStep,
    StepResult,
    WorkflowRun as PlaybookRun,
    step,
)

from coactra.workflow.runtime import (
    ApprovalStatus,
    ApprovalStore,
    AsyncProcedureRunnerAdapter,
    InMemoryApprovalStore,
    PendingApproval,
    ProcedureRunner,
    RunContext,
    WorkflowEngine,
    WorkflowInterrupt,
    WorkflowNotResumableError,
    WorkflowRun,
    WorkflowRunStatus,
    WorkflowRuntime,
    make_default_workflow_engine,
    make_workflow_engine,
    Capability,
    CapabilityRegistry,
    CapabilityValidationError,
    CapabilityValidationIssue,
    InMemoryCapabilityRegistry,
    ToolInvoker,
    VerificationResult,
)
from coactra.workflow.runtime.handlers import (
    Approver,
    AutoApprove,
    Collaborator,
    Escalation,
    EscalationRouter,
    EscalationUnresolved,
    NullCollaborator,
    RejectAll,
    TerminalHumanRouter,
)
from coactra.workflow.promotion import (
    CandidateStatus,
    InMemoryProcedurePromotionStore,
    ProcedureCandidate,
    ProcedureVersion,
)
from coactra.workflow.induction import ReasoningTrace, induce, update

try:
    from coactra.workflow.backends.langgraph import LangGraphEngine
except ImportError as exc:  # pragma: no cover - only when langgraph is not installed
    _LANGGRAPH_IMPORT_ERROR = exc

    class LangGraphEngine:
        def __init__(self, *args, **kwargs) -> None:
            raise ImportError(
                "LangGraphEngine requires the langgraph dependency"
            ) from _LANGGRAPH_IMPORT_ERROR


try:
    from coactra.workflow.backends.durable_langgraph import (
        DurableLangGraphEngine,
        build_graph,
        check_done_criteria,
        document_from_procedure,
        run_workflow,
        verify_done_criteria,
    )
except ImportError as exc:  # pragma: no cover - only when optional deps are missing
    _DURABLE_LANGGRAPH_IMPORT_ERROR = exc

    class DurableLangGraphEngine:
        def __init__(self, *args, **kwargs) -> None:
            raise ImportError(
                "DurableLangGraphEngine requires the langgraph dependency"
            ) from _DURABLE_LANGGRAPH_IMPORT_ERROR

    def _missing_durable_langgraph(*args, **kwargs):
        raise ImportError(
            "Durable LangGraph helpers require the langgraph dependency"
        ) from _DURABLE_LANGGRAPH_IMPORT_ERROR

    build_graph = _missing_durable_langgraph
    check_done_criteria = _missing_durable_langgraph
    document_from_procedure = _missing_durable_langgraph
    run_workflow = _missing_durable_langgraph
    verify_done_criteria = _missing_durable_langgraph


from coactra.workflow.domain.models import Procedure, RunResult, Step
from coactra.workflow.domain.scope import Scope
from coactra.workflow.store import InMemoryProcedureStore, ProcedureStore
from coactra.workflow.routing import (
    TenantProcedureStoreRouter,
    TenantWorkflowEngineRouter,
)
from coactra.workflow.ledger import (
    AgentSpec,
    ApprovalRequest,
    Artifact,
    ArtifactPart,
    ArtifactRef,
    Assignment,
    Attempt,
    AttemptStatus,
    AuditContext,
    Budget,
    CapabilityDescriptor,
    CapabilityRequirement,
    CapabilitySet,
    Checkpoint,
    Deadline,
    Decision,
    DecisionOutcome,
    ElicitationRequest,
    EventEnvelope,
    ExecutionPlan,
    ExecutionReceipt,
    InMemoryWorkStore,
    InvalidTransitionError,
    Lease,
    LeaseError,
    Provenance,
    ResumeToken,
    RetryPolicy,
    Scope as WorkScope,
    SkillSpec,
    SqlWorkStore,
    TenantWorkStoreRouter,
    WorkError,
    WorkManager,
    WorkNotFoundError,
    WorkOrder,
    WorkStatus,
    WorkStore,
    WorkStoreReport,
    check_work_store_contract,
)
from coactra.workflow.ledger_facade import (
    DurableOrchestrationResult,
    DurableOrchestrator,
    OrchestrationResult,
    Orchestrator,
    ProcedureNotFoundError,
    WorkflowEngineRequiredError,
)

__version__ = distribution_version()

__all__ = [
    "__version__",
    "Workflow",
    "Playbook",
    "PlaybookStep",
    "step",
    "StepResult",
    "Approval",
    "PlaybookRun",
    "Scope",
    "Step",
    "Procedure",
    "RunResult",
    "RunContext",
    "Capability",
    "CapabilityRegistry",
    "CapabilityValidationError",
    "CapabilityValidationIssue",
    "InMemoryCapabilityRegistry",
    "ToolInvoker",
    "VerificationResult",
    "ProcedureRunner",
    "WorkflowEngine",
    "WorkflowRun",
    "WorkflowRunStatus",
    "WorkflowInterrupt",
    "WorkflowRuntime",
    "make_default_workflow_engine",
    "make_workflow_engine",
    "WorkflowNotResumableError",
    "AsyncProcedureRunnerAdapter",
    "ApprovalStatus",
    "ApprovalStore",
    "PendingApproval",
    "InMemoryApprovalStore",
    "LangGraphEngine",
    "DurableLangGraphEngine",
    "build_graph",
    "run_workflow",
    "document_from_procedure",
    "check_done_criteria",
    "verify_done_criteria",
    "ReasoningTrace",
    "induce",
    "update",
    "Approver",
    "Collaborator",
    "EscalationRouter",
    "Escalation",
    "EscalationUnresolved",
    "AutoApprove",
    "RejectAll",
    "NullCollaborator",
    "TerminalHumanRouter",
    "ProcedureStore",
    "InMemoryProcedureStore",
    "CandidateStatus",
    "ProcedureCandidate",
    "ProcedureVersion",
    "InMemoryProcedurePromotionStore",
    "TenantProcedureStoreRouter",
    "TenantWorkflowEngineRouter",
    "AgentSpec",
    "ApprovalRequest",
    "Artifact",
    "ArtifactPart",
    "ArtifactRef",
    "Assignment",
    "Attempt",
    "AttemptStatus",
    "AuditContext",
    "Budget",
    "CapabilityDescriptor",
    "CapabilityRequirement",
    "CapabilitySet",
    "Checkpoint",
    "Deadline",
    "Decision",
    "DecisionOutcome",
    "DurableOrchestrationResult",
    "DurableOrchestrator",
    "ElicitationRequest",
    "EventEnvelope",
    "ExecutionPlan",
    "ExecutionReceipt",
    "InMemoryWorkStore",
    "InvalidTransitionError",
    "Lease",
    "LeaseError",
    "OrchestrationResult",
    "Orchestrator",
    "ProcedureNotFoundError",
    "Provenance",
    "ResumeToken",
    "RetryPolicy",
    "SkillSpec",
    "SqlWorkStore",
    "TenantWorkStoreRouter",
    "WorkError",
    "WorkManager",
    "WorkNotFoundError",
    "WorkOrder",
    "WorkScope",
    "WorkStatus",
    "WorkStore",
    "WorkStoreReport",
    "WorkflowEngineRequiredError",
    "check_work_store_contract",
]


def __getattr__(name: str) -> Any:
    if name == "Workflow":
        return getattr(import_module("coactra.agent.workflow"), name)
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
