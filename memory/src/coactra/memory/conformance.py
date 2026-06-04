"""Reusable contract probes for memory backend adapters."""

from __future__ import annotations

import uuid

from pydantic import BaseModel, Field

from coactra.memory.backends.base import MemoryBackend
from coactra.memory.capabilities import Capability
from coactra.memory.types import Scope


class MemoryBackendReport(BaseModel):
    backend: str
    capabilities: set[Capability] = Field(default_factory=set)
    recall_count: int = 0
    dump_count: int = 0


async def check_memory_backend_contract(
    backend: MemoryBackend,
    *,
    scope: Scope | None = None,
) -> MemoryBackendReport:
    """Exercise the minimal public backend contract against an isolated scope."""

    probe_scope = scope or Scope(tenant=f"contract-{uuid.uuid4().hex}")
    marker = f"contract memory marker {uuid.uuid4().hex}"
    await backend.remember([marker], probe_scope)
    hits = await backend.recall("contract memory marker", probe_scope, k=3)
    items = await backend.dump(probe_scope)
    caps = await backend.capabilities()
    if not hits:
        raise AssertionError("backend recall returned no results for the probe memory")
    if not items:
        raise AssertionError("backend dump returned no results for the probe memory")
    return MemoryBackendReport(
        backend=type(backend).__name__,
        capabilities=caps,
        recall_count=len(hits),
        dump_count=len(items),
    )
