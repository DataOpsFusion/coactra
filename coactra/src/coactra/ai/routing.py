"""Tenant-routed reasoning stores for hard physical silo isolation."""
from __future__ import annotations

from collections.abc import Callable
from typing import Any

from coactra.ai.protocols import ReasoningStore


class TenantReasoningStoreRouter:
    """Delegate reasoning records to one cached physical store per tenant."""

    def __init__(self, factory: Callable[[str], ReasoningStore]) -> None:
        self._factory = factory
        self._stores: dict[str, ReasoningStore] = {}

    def for_tenant(self, tenant: str) -> ReasoningStore:
        backend = self._stores.get(tenant)
        if backend is None:
            backend = self._factory(tenant)
            self._stores[tenant] = backend
        return backend

    def put(self, tenant: str, trace: Any) -> None:
        self.for_tenant(tenant).put(tenant, trace)

    def search(self, tenant: str, vector: list[float], k: int, min_quality: float):
        return self.for_tenant(tenant).search(tenant, vector, k, min_quality)

    def get(self, tenant: str, trace_id: str) -> Any | None:
        return self.for_tenant(tenant).get(tenant, trace_id)
