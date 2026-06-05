"""Per-tenant lazy-cache base shared by capability routers."""
from __future__ import annotations

from collections.abc import Callable
from typing import Generic, TypeVar

T = TypeVar("T")


class TenantRouter(Generic[T]):
    """Build and cache exactly one physical backend ``T`` per tenant id."""

    def __init__(self, factory: Callable[[str], T]) -> None:
        self._factory = factory
        self._cache: dict[str, T] = {}

    def for_tenant(self, tenant_id: str) -> T:
        backend = self._cache.get(tenant_id)
        if backend is None:
            backend = self._factory(tenant_id)
            self._cache[tenant_id] = backend
        return backend
