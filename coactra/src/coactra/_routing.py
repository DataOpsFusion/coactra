"""Canonical per-tenant lazy-cache base for every silo router in ``coactra``.

Each capability's tenant router (work store, procedure store, workflow engine,
reasoning store, memory backend, workspace backend, org store, agent runtime) needs
the same thing: lazily build one physical backend per tenant and cache it. That
caching policy lives here once — the per-capability routers add only their thin,
contract-specific delegators that forward to ``for_tenant(...)`` (or, where the
backend is keyed by a richer object than a tenant-id string, wrap an instance of this
class). This module sits at the package root, alongside :mod:`coactra.scope`, so every
capability shares the one implementation instead of hand-rolling its own.

The cache key is whatever is passed to :meth:`TenantRouter.for_tenant`; it is typed as
``str`` for the common tenant-id case, but any hashable key works (the agent router
keys by a frozen ``Scope``).
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
