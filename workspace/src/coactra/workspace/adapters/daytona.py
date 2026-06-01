"""Daytona adapter — STUB. Persistent sandboxes + snapshots; raises until the daytona extra."""

from __future__ import annotations

from coactra.workspace.adapters._stub import require_extra


class DaytonaBackend:
    def __init__(self, *args, **kwargs) -> None:
        require_extra("daytona")
