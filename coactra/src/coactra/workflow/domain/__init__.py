"""Workflow domain data structures."""

from coactra.scope import Scope
from coactra.workflow.domain.models import Procedure, RunResult, Step, StepKind

__all__ = ["Scope", "StepKind", "Step", "Procedure", "RunResult"]
