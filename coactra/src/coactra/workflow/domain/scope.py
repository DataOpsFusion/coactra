"""Scope — the tenant-scoped key threaded through every run and the procedure store.

Same shape as the sibling capabilities: ``tenant_id`` + ``namespace``, defined once in
:class:`coactra.scope._TenantNamespaceScope` and re-exported here under the package-local
``Scope`` name. Isolation is first-class — nothing crosses a (tenant_id, namespace)
boundary unless code explicitly moves it.
"""

from __future__ import annotations

from coactra.scope import _TenantNamespaceScope


class Scope(_TenantNamespaceScope):
    """Immutable, hashable tenant + namespace key."""
