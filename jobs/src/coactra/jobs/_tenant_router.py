"""Shared per-tenant lazy-cache base for this package's silo routers.

Every tenant router in ``coactra-jobs`` (work store, procedure store, workflow
engine) needs the same thing: lazily build one physical backend per tenant and cache it.
That caching policy lives here once — subclasses add only their thin, contract-specific
delegators that forward to ``for_tenant(...)``. Kept package-private: this is internal
wiring for orchestration, deliberately NOT a cross-package abstraction (the sibling
libraries each own their own router, so the packages don't tangle).
"""
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
