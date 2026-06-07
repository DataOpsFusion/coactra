"""Tenant scope threaded through every work operation.

The ``tenant_id`` + ``namespace`` shape is defined once in
:class:`coactra.scope._TenantNamespaceScope`; this module re-exports it under the
package-local ``Scope`` name.
"""

from __future__ import annotations

from coactra.scope import _TenantNamespaceScope


class Scope(_TenantNamespaceScope):
    """Immutable tenant + namespace key."""
