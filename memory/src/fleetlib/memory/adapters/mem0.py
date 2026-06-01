"""Mem0 adapter — STUB. Declares capabilities; raises until the mem0 extra + impl land."""

from __future__ import annotations

from fleetlib.memory.adapters._stub import require_extra
from fleetlib.memory.capabilities import Capability


class Mem0Backend:
    declared_capabilities = {
        Capability.STORE,
        Capability.VECTOR_EMBEDDING,
        Capability.PROVENANCE,
    }

    def __init__(self, *args, **kwargs) -> None:
        require_extra("mem0")
