"""Back-compat shim — the Neo4j stub now lives in ``repository.neo4j_store``."""

from __future__ import annotations

from fleetlib.organization.repository.neo4j_store import Neo4jOrgStore

__all__ = ["Neo4jOrgStore"]
