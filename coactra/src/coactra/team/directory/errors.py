"""Organization errors.

CrossTenantError  — raised when an operation would link or read across a tenant
                    boundary. Isolation is the core invariant; a breach is loud.
MissingExtraError — raised when an optional-extra backend is used before its extra
                    (and a real implementation) exist.
"""

from __future__ import annotations

# Re-export the canonical MissingExtraError; kept importable from this path.
from coactra.errors import MissingExtraError

__all__ = ["CrossTenantError", "MissingExtraError"]


class CrossTenantError(ValueError):
    """An operation tried to span two tenants. Multi-tenant isolation forbids it."""
