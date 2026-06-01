"""A2A adapter — STUB. Will satisfy A2ATransportPort; raises until the a2a extra."""

from __future__ import annotations

from coactra.agent.adapters._stub import require_extra


class A2ATransport:
    satisfies = "A2ATransportPort"

    def __init__(self, *args, **kwargs) -> None:
        require_extra("a2a")
