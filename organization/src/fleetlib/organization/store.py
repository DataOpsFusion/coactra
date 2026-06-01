"""Back-compat shim — the OrgStore Protocol now lives in ``repository.store``.

Kept so ``from fleetlib.organization.store import OrgStore`` (and ``Directory``)
continue to resolve after the v0.2 layering split.
"""

from __future__ import annotations

from fleetlib.organization.repository.store import Directory, OrgStore

__all__ = ["OrgStore", "Directory"]
