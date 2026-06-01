"""Repository layer — the persistence SPI and its backends (the swappable seam).

``OrgStore`` is the Protocol every backend satisfies; ``Directory`` is the bulk-read
result type. ``SqliteOrgStore`` is the one working default; ``Neo4jOrgStore`` is the
optional-extra stub. These are injected into the service layer (load/save), never
instantiated by the domain aggregate.
"""

from __future__ import annotations

from fleetlib.organization.repository.neo4j_store import Neo4jOrgStore
from fleetlib.organization.repository.sqlite_store import SqliteOrgStore
from fleetlib.organization.repository.store import Directory, OrgStore

__all__ = [
    "OrgStore",
    "Directory",
    "SqliteOrgStore",
    "Neo4jOrgStore",
]
