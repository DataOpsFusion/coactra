"""Workflow domain data structures."""

from coactra.jobs.workflow.domain.models import Procedure, RunResult, Step, StepKind
from coactra.jobs.workflow.domain.scope import Scope

__all__ = ["Scope", "StepKind", "Step", "Procedure", "RunResult"]
