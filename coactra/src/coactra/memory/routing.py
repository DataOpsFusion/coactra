"""Tenant-routed memory backends for hard physical silo isolation."""

from __future__ import annotations

from collections.abc import Sequence

from coactra._routing import TenantRouter
from coactra.memory.backends.base import MemoryExporter, MemoryReader, MemoryWriter
from coactra.memory.capabilities import Capability
from coactra.memory.export import ExportReport
from coactra.memory.types import MemoryEvent, Recollection, Scope


class TenantMemoryRouter(TenantRouter[MemoryReader]):
    """Delegate each scoped operation to one cached backend per tenant.

    Caching/dispatch comes from :class:`coactra._routing.TenantRouter`; this subclass
    adds memory contract delegators plus capability intersection across
    the live per-tenant backends.
    """

    async def capabilities(self) -> set[Capability]:
        """Routers may span heterogeneous silos; advertise only universal capabilities."""
        if not self._cache:
            return set()
        per_backend = []
        for backend in self._cache.values():
            capabilities = getattr(backend, "capabilities", None)
            if capabilities is not None:
                per_backend.append(await capabilities())
        if not per_backend:
            return set()
        return set.intersection(*per_backend)

    async def remember(self, events: Sequence[MemoryEvent], scope: Scope) -> None:
        backend = self.for_tenant(scope.tenant)
        if not isinstance(backend, MemoryWriter):
            raise TypeError("tenant memory backend does not support remember()")
        await backend.remember(events, scope)

    async def recall(self, query: str, scope: Scope, k: int = 10) -> list[Recollection]:
        return await self.for_tenant(scope.tenant).recall(query, scope, k)

    async def dump(self, scope: Scope) -> list[Recollection]:
        backend = self.for_tenant(scope.tenant)
        if not isinstance(backend, MemoryExporter):
            raise TypeError("tenant memory backend does not support dump()")
        return await backend.dump(scope)

    async def ingest(self, items: Sequence[Recollection], scope: Scope) -> ExportReport:
        backend = self.for_tenant(scope.tenant)
        if not isinstance(backend, MemoryExporter):
            raise TypeError("tenant memory backend does not support ingest()")
        return await backend.ingest(items, scope)
