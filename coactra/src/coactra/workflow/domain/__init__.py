"""Workflow domain data structures."""

from coactra.workflow.domain.models import Procedure, RunResult, Step, StepKind
from coactra.workflow.domain.scope import Scope

__all__ = ["Scope", "StepKind", "Step", "Procedure", "RunResult"]
