"""E2B adapter — STUB. Pause/resume fs + process; raises until the e2b extra."""

from __future__ import annotations

from fleetlib.workspace.adapters._stub import require_extra


class E2BBackend:
    def __init__(self, *args, **kwargs) -> None:
        require_extra("e2b")
