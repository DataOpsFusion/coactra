"""Tenant-routed memory backends for hard physical silo isolation."""
from __future__ import annotations

from collections.abc import Sequence

from coactra._routing import TenantRouter
from coactra.memory.backends.base import MemoryBackend
from coactra.memory.capabilities import Capability
from coactra.memory.export import ExportReport
from coactra.memory.types import MemoryEvent, Recollection, Scope


class TenantMemoryBackendRouter(TenantRouter[MemoryBackend]):
    """Delegate each scoped operation to one cached backend per tenant.

    Caching/dispatch comes from :class:`coactra._routing.TenantRouter`; this subclass
    adds the ``MemoryBackend`` contract delegators plus capability intersection across
    the live per-tenant backends.
    """

    async def capabilities(self) -> set[Capability]:
        """Routers may span heterogeneous silos; advertise only universal capabilities."""
        if not self._cache:
            return set()
        per_backend = [await backend.capabilities() for backend in self._cache.values()]
        return set.intersection(*per_backend)

    async def remember(self, events: Sequence[MemoryEvent], scope: Scope) -> None:
        await self.for_tenant(scope.tenant).remember(events, scope)

    async def recall(self, query: str, scope: Scope, k: int = 10) -> list[Recollection]:
        return await self.for_tenant(scope.tenant).recall(query, scope, k)

    async def dump(self, scope: Scope) -> list[Recollection]:
        return await self.for_tenant(scope.tenant).dump(scope)

    async def ingest(self, items: Sequence[Recollection], scope: Scope) -> ExportReport:
        return await self.for_tenant(scope.tenant).ingest(items, scope)
