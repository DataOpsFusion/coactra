"""Graphiti adapter — STUB. Declares graph/temporal capabilities; raises until graphiti extra."""

from __future__ import annotations

from fleetlib.memory.adapters._stub import require_extra
from fleetlib.memory.capabilities import Capability


class GraphitiBackend:
    declared_capabilities = {
        Capability.STORE,
        Capability.GRAPH_EDGES,
        Capability.TEMPORAL,
        Capability.PROVENANCE,
    }

    def __init__(self, *args, **kwargs) -> None:
        require_extra("graphiti")
