"""Repository layer — the persistence SPI and its backends (the swappable seam).

``OrgStore`` is the Protocol every backend satisfies; ``Directory`` is the bulk-read
result type. ``SqliteOrgStore`` is the one working default. These are injected into
the service layer (load/save), never instantiated by the domain aggregate.
"""

from __future__ import annotations

from coactra.directory.repository.async_store import AsyncOrgStore, AsyncPostgresOrgStore
from coactra.directory.repository.routing import TenantOrgStoreRouter
from coactra.directory.repository.sqlite_store import SqliteOrgStore
from coactra.directory.repository.store import Directory, OrgStore

__all__ = [
    "OrgStore",
    "Directory",
    "SqliteOrgStore",
    "AsyncOrgStore",
    "AsyncPostgresOrgStore",
    "TenantOrgStoreRouter",
]
