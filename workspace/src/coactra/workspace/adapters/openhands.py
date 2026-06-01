"""OpenHands adapter — STUB. Persists conversation + tools + agent state; raises until the openhands extra."""

from __future__ import annotations

from coactra.workspace.adapters._stub import require_extra


class OpenHandsBackend:
    def __init__(self, *args, **kwargs) -> None:
        require_extra("openhands")
