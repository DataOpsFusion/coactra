"""WorkflowEngine — the swappable execution seam, plus the RunContext it consumes.

ONE working default implements this: LangGraphEngine. Temporal/Prefect are stubs. The
RunContext carries the scope (multi-tenant) and the injected handlers so the engine never
hard-codes approval/collaboration/escalation behavior.
"""

from __future__ import annotations

from typing import Any, Protocol, runtime_checkable

from pydantic import BaseModel, Field

from fleetlib.workflow.handlers import (
    Approver,
    AutoApprove,
    Collaborator,
    EscalationRouter,
    NullCollaborator,
    TerminalHumanRouter,
)
from fleetlib.workflow.models import Procedure, RunResult
from fleetlib.workflow.scope import Scope


class RunContext(BaseModel):
    """Everything a run needs beyond the procedure + state: tenant scope and handlers."""

    model_config = {"arbitrary_types_allowed": True}

    scope: Scope
    approver: Approver = Field(default_factory=AutoApprove)
    collaborator: Collaborator = Field(default_factory=NullCollaborator)
    router: EscalationRouter = Field(default_factory=TerminalHumanRouter)
    chain: list[str] = Field(default_factory=list)  # the org chain for escalate steps


@runtime_checkable
class WorkflowEngine(Protocol):
    def run(
        self, procedure: Procedure, state: dict[str, Any], ctx: RunContext
    ) -> RunResult:
        """Compile and execute a procedure within ctx.scope, returning output + path."""
        ...
