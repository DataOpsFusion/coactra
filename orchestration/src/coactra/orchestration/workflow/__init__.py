"""coactra.orchestration.workflow — a thin, learnable workflow layer over a durable engine.

A Procedure is a DATA STRUCTURE: an authored flow and an induced (learned) flow are the
SAME type and run the SAME compile->run path on the default LangGraph engine. Steps may
collaborate (ask another agent) or escalate up the org until a decider resolves it.
workflow owns when/what; organization routes who; agent carries the talk. Induction is
trace-faithful and deterministic; update() is manual — we do NOT overclaim self-learning.
"""

from coactra.orchestration.workflow.runtime import (
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
from coactra.orchestration.workflow.runtime.handlers import (
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
from coactra.orchestration.workflow.promotion import (
    CandidateStatus,
    InMemoryProcedurePromotionStore,
    ProcedureCandidate,
    ProcedureVersion,
)
from coactra.orchestration.workflow.induction import ReasoningTrace, induce, update

try:
    from coactra.orchestration.workflow.backends.langgraph import LangGraphEngine
except ImportError as exc:  # pragma: no cover - only when langgraph is not installed
    _LANGGRAPH_IMPORT_ERROR = exc

    class LangGraphEngine:
        def __init__(self, *args, **kwargs) -> None:
            raise ImportError(
                "LangGraphEngine requires the langgraph dependency"
            ) from _LANGGRAPH_IMPORT_ERROR


try:
    from coactra.orchestration.workflow.backends.durable_langgraph import (
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


from coactra.orchestration.workflow.domain.models import Procedure, RunResult, Step
from coactra.orchestration.workflow.domain.scope import Scope
from coactra.orchestration.workflow.store import InMemoryProcedureStore, ProcedureStore
from coactra.orchestration.workflow.routing import (
    TenantProcedureStoreRouter,
    TenantWorkflowEngineRouter,
)

__version__ = "0.1.0"

__all__ = [
    "__version__",
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
]
