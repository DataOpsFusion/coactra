"""Temporal adapter — STUB. Will satisfy WorkflowEngine; raises until the temporal extra."""

from __future__ import annotations

from fleetlib.workflow.adapters._stub import require_extra


class TemporalEngine:
    satisfies = "WorkflowEngine"

    def __init__(self, *args, **kwargs) -> None:
        require_extra("temporal")
