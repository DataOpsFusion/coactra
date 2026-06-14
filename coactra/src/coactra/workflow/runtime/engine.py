"""Local procedure execution context and synchronous runner boundary.

``ProcedureRunner`` is the small run-to-completion seam implemented by the local
local Procedure runner. Durable runtimes implement the async ``WorkflowEngine`` contract from
``runtime.durable`` instead: start/resume with a stable thread id.
"""

from __future__ import annotations

from typing import Any, Protocol, runtime_checkable

from pydantic import BaseModel, Field

from coactra.workflow.domain.models import Procedure, RunResult
from coactra.workflow.domain.scope import Scope
from coactra.workflow.runtime.handlers import (
    Approver,
    AutoApprove,
    Collaborator,
    EscalationRouter,
    NullCollaborator,
    TerminalHumanRouter,
)


class RunContext(BaseModel):
    """Everything a run needs beyond the procedure and state."""

    model_config = {"arbitrary_types_allowed": True}

    scope: Scope
    approver: Approver = Field(default_factory=AutoApprove)
    collaborator: Collaborator = Field(default_factory=NullCollaborator)
    router: EscalationRouter = Field(default_factory=TerminalHumanRouter)
    chain: list[str] = Field(default_factory=list)


@runtime_checkable
class ProcedureRunner(Protocol):
    """Synchronous local execution seam for run-to-completion engines."""

    def run(self, procedure: Procedure, state: dict[str, Any], ctx: RunContext) -> RunResult:
        """Compile and execute a procedure within ``ctx.scope``."""
        ...
