"""Tenant-routed reasoning stores for hard physical silo isolation."""
from __future__ import annotations

from typing import Any

from coactra._routing import TenantRouter
from coactra.ai.protocols import ReasoningStore


class TenantReasoningStoreRouter(TenantRouter[ReasoningStore]):
    """Delegate reasoning records to one cached physical store per tenant.

    Caching/dispatch comes from :class:`coactra._routing.TenantRouter`; this subclass
    adds only the ``ReasoningStore`` contract delegators.
    """

    def put(self, tenant: str, trace: Any) -> None:
        self.for_tenant(tenant).put(tenant, trace)

    def search(self, tenant: str, vector: list[float], k: int, min_quality: float):
        return self.for_tenant(tenant).search(tenant, vector, k, min_quality)

    def get(self, tenant: str, trace_id: str) -> Any | None:
        return self.for_tenant(tenant).get(tenant, trace_id)
