"""Workflow domain data structures."""

from coactra.orchestration.workflow.domain.models import Procedure, RunResult, Step, StepKind
from coactra.orchestration.workflow.domain.scope import Scope

__all__ = ["Scope", "StepKind", "Step", "Procedure", "RunResult"]
