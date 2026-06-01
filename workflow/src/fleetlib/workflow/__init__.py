"""fleetlib.workflow — a thin, learnable workflow layer over a durable engine.

A Procedure is a DATA STRUCTURE: an authored flow and an induced (learned) flow are the
SAME type and run the SAME compile->run path on the default LangGraph engine. Steps may
collaborate (ask another agent) or escalate up the org until a decider resolves it.
workflow owns when/what; organization routes who; agent carries the talk. Induction is
trace-faithful and deterministic; update() is manual — we do NOT overclaim self-learning.
"""

from fleetlib.workflow.engine import RunContext, WorkflowEngine
from fleetlib.workflow.handlers import (
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
from fleetlib.workflow.induction import ReasoningTrace, induce, update
from fleetlib.workflow.langgraph_engine import LangGraphEngine
from fleetlib.workflow.models import Procedure, RunResult, Step
from fleetlib.workflow.scope import Scope
from fleetlib.workflow.store import InMemoryProcedureStore, ProcedureStore

__version__ = "0.1.0"

__all__ = [
    "__version__",
    "Scope",
    "Step",
    "Procedure",
    "RunResult",
    "RunContext",
    "WorkflowEngine",
    "LangGraphEngine",
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
]
