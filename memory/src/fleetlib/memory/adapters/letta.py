"""Letta adapter — STUB. Declares memory-block capabilities; raises until letta extra."""

from __future__ import annotations

from fleetlib.memory.adapters._stub import require_extra
from fleetlib.memory.capabilities import Capability


class LettaBackend:
    declared_capabilities = {
        Capability.STORE,
        Capability.MEMORY_BLOCK,
        Capability.PROVENANCE,
    }

    def __init__(self, *args, **kwargs) -> None:
        require_extra("letta")
