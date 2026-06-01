"""Back-compat shim — the OrgStore Protocol now lives in ``repository.store``.

Kept so ``from coactra.organization.store import OrgStore`` (and ``Directory``)
continue to resolve after the v0.2 layering split.
"""

from __future__ import annotations

from coactra.organization.repository.store import Directory, OrgStore

__all__ = ["OrgStore", "Directory"]
