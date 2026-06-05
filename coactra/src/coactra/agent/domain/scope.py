"""Scope — the tenant-scoped key threaded through every subsystem of the agent.

Same shape as every sibling capability: ``tenant_id`` + ``namespace``. The shape now
lives in exactly one place — :class:`coactra.scope._TenantNamespaceScope` — and this
module re-exports it under the package-local ``Scope`` name. Isolation is first-class —
a mount, a delegation, and a collaboration check all carry a Scope, and nothing crosses
a (tenant_id, namespace) boundary unless code explicitly moves it.
"""

from __future__ import annotations

from coactra.scope import _TenantNamespaceScope


class Scope(_TenantNamespaceScope):
    """Immutable, hashable tenant + namespace key."""
