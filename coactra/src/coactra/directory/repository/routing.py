"""Tenant-routed organization stores for hard physical silo isolation."""
from __future__ import annotations

from collections.abc import Callable
from typing import Any

from coactra.directory.models import Tenant
from coactra.directory.repository.store import ORG_STORE_METHODS, OrgStore


class TenantOrgStoreRouter:
    """Delegate each tenant operation to one cached physical ``OrgStore``."""

    def __init__(self, factory: Callable[[str], OrgStore]) -> None:
        self._factory = factory
        self._stores: dict[str, OrgStore] = {}

    def for_tenant(self, tenant_id: str) -> OrgStore:
        store = self._stores.get(tenant_id)
        if store is None:
            store = self._factory(tenant_id)
            self._stores[tenant_id] = store
        return store

    def add_tenant(self, tenant: Tenant):
        return self.for_tenant(tenant.tenant_id).add_tenant(tenant)

    def __getattr__(self, name: str):
        """Catch-all router for any non-Protocol extra (e.g. resolve_decider), keyed on the
        mandatory first ``tenant_id`` argument. The Protocol surface is bound as real
        methods by the loop below so isinstance(x, OrgStore) holds without faking it here.
        """
        def routed(tenant_id: str, *args: Any, **kwargs: Any):
            return getattr(self.for_tenant(tenant_id), name)(tenant_id, *args, **kwargs)
        return routed


def _routed(name: str):
    def call(self, tenant_id: str, *args: Any, **kwargs: Any):
        return getattr(self.for_tenant(tenant_id), name)(tenant_id, *args, **kwargs)
    call.__name__ = name
    return call


# Bind the directory SPI (derived from the Protocol — never hand-synced) as real routing
# methods. ``add_tenant`` is the lone exception: it routes by ``tenant.tenant_id``, not a
# leading ``tenant_id`` argument, so it stays an explicit method above.
for _name in ORG_STORE_METHODS:
    if _name != "add_tenant":
        setattr(TenantOrgStoreRouter, _name, _routed(_name))
