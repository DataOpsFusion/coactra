"""coactra.workflow — public playbooks plus durable Procedure engines.

Workflow owns the definition and run ledger: authored flows, induced procedures,
approvals, checkpoints, and runtime adapters. Team/directory policy decides who may act;
agent transports carry the talk. Induction is trace-faithful and deterministic; update()
is manual so the library does not overclaim self-learning.
"""

from importlib import import_module
from typing import Any

from coactra._version import distribution_version
from coactra.workflow.domain.models import Procedure, RunResult, Step
from coactra.workflow.domain.scope import Scope
from coactra.workflow.induction import ReasoningTrace, induce, update
from coactra.workflow.playbook import (
    Approval,
    Playbook,
    ProofBundle,
    StepResult,
    VerificationReceipt,
    step,
)
from coactra.workflow.playbook import (
    Step as PlaybookStep,
)
from coactra.workflow.playbook import (
    WorkflowRun as PlaybookRun,
)
from coactra.workflow.promotion import (
    CandidateStatus,
    InMemoryProcedurePromotionStore,
    ProcedureCandidate,
    ProcedureVersion,
)
from coactra.workflow.store import InMemoryProcedureStore, ProcedureStore

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
    from coactra.workflow.backends.durable_langgraph import DurableLangGraphEngine
except ImportError as exc:  # pragma: no cover - only when optional deps are missing
    _DURABLE_LANGGRAPH_IMPORT_ERROR = exc

    class DurableLangGraphEngine:
        def __init__(self, *args, **kwargs) -> None:
            raise ImportError(
                "DurableLangGraphEngine requires the langgraph dependency"
            ) from _DURABLE_LANGGRAPH_IMPORT_ERROR


__version__ = distribution_version()

_LAZY_RUNTIME_EXPORTS = frozenset(
    {
        "ApprovalStatus",
        "ApprovalStore",
        "AsyncProcedureRunnerAdapter",
        "InMemoryApprovalStore",
        "PendingApproval",
        "ProcedureRunner",
        "RunContext",
        "WorkflowEngine",
        "WorkflowInterrupt",
        "WorkflowNotResumableError",
        "WorkflowRun",
        "WorkflowRunStatus",
        "WorkflowRuntime",
        "make_default_workflow_engine",
        "make_workflow_engine",
        "Capability",
        "CapabilityRegistry",
        "CapabilityValidationError",
        "CapabilityValidationIssue",
        "InMemoryCapabilityRegistry",
        "ToolInvoker",
        "VerificationResult",
    }
)

_LAZY_HANDLER_EXPORTS = frozenset(
    {
        "Approver",
        "AutoApprove",
        "Collaborator",
        "Escalation",
        "EscalationRouter",
        "EscalationUnresolved",
        "NullCollaborator",
        "RejectAll",
        "TerminalHumanRouter",
    }
)

_LAZY_ROUTING_EXPORTS = frozenset(
    {
        "TenantProcedureStoreRouter",
        "TenantWorkflowEngineRouter",
    }
)

_LAZY_LEDGER_FACADE_EXPORTS = frozenset(
    {
        "DurableOrchestrationResult",
        "DurableOrchestrator",
        "OrchestrationResult",
        "Orchestrator",
        "ProcedureNotFoundError",
        "WorkflowEngineRequiredError",
    }
)

__all__ = [
    "__version__",
    "Workflow",
    "Playbook",
    "PlaybookStep",
    "step",
    "StepResult",
    "VerificationReceipt",
    "ProofBundle",
    "Approval",
    "PlaybookRun",
    "Scope",
    "Step",
    "Procedure",
    "RunResult",
    "RunContext",
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
    "DurableOrchestrationResult",
    "DurableOrchestrator",
    "OrchestrationResult",
    "Orchestrator",
    "ProcedureNotFoundError",
    "WorkflowEngineRequiredError",
]


def __getattr__(name: str) -> Any:
    if name == "Workflow":
        return getattr(import_module("coactra.agent.workflow"), name)
    if name in _LAZY_RUNTIME_EXPORTS:
        runtime = import_module("coactra.workflow.runtime")
        return getattr(runtime, name)
    if name in _LAZY_HANDLER_EXPORTS:
        handlers = import_module("coactra.workflow.runtime.handlers")
        return getattr(handlers, name)
    if name in _LAZY_ROUTING_EXPORTS:
        routing = import_module("coactra.workflow.routing")
        return getattr(routing, name)
    if name in _LAZY_LEDGER_FACADE_EXPORTS:
        ledger_facade = import_module("coactra.workflow.ledger_facade")
        return getattr(ledger_facade, name)
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
