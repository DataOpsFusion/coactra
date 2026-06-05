"""Back-compat shim: the canonical generic now lives in :mod:`coactra._routing`."""
from coactra._routing import TenantRouter

__all__ = ["TenantRouter"]
