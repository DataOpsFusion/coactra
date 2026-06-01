"""Prefect adapter — STUB. Will satisfy WorkflowEngine; raises until the prefect extra."""

from __future__ import annotations

from coactra.workflow.adapters._stub import require_extra


class PrefectEngine:
    satisfies = "WorkflowEngine"

    def __init__(self, *args, **kwargs) -> None:
        require_extra("prefect")
