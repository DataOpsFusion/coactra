"""Factory — the composition root that selects an OrgStore backend from a config URL.

``make_org_store("sqlite://")`` returns the default SQLite-backed store;
``make_org_store("sqlite:///path/org.db")`` a file-backed one; ``neo4j://…`` routes to
the (raise-on-use) Neo4j stub. The aggregate NEVER instantiates a store inline — this
function is the one place a backend is chosen, then injected into the service layer.
"""

from __future__ import annotations

from fleetlib.organization.engine import make_engine
from fleetlib.organization.repository.neo4j_store import Neo4jOrgStore
from fleetlib.organization.repository.sqlite_store import SqliteOrgStore
from fleetlib.organization.store import OrgStore


def make_org_store(config: str = "sqlite://") -> OrgStore:
    """Return an OrgStore for the given backend config URL.

    Supported schemes:
      - ``sqlite://`` / ``sqlite:///path`` — the default SQLModel-backed store.
      - ``neo4j://…``                      — the optional-extra stub (raises on use).
    Any other scheme is an unsupported backend.
    """
    if config.startswith("sqlite"):
        return SqliteOrgStore(engine=make_engine(config))
    if config.startswith("neo4j"):
        return Neo4jOrgStore(uri=config)
    raise ValueError(f"unsupported org-store backend: {config!r}")
