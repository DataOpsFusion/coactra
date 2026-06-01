"""Neo4j adapter — STUB. Reporting edges are naturally graph-shaped, so a graph store is
the honest 'swap the backend' demonstration. Raises until the neo4j extra + impl land."""

from __future__ import annotations

from coactra.organization.errors import MissingExtraError


class Neo4jOrgStore:
    def __init__(self, *args, **kwargs) -> None:
        raise MissingExtraError(
            "Neo4jOrgStore requires the optional 'neo4j' extra and a real implementation; "
            "install with: pip install coactra-organization[neo4j] (stub not yet implemented)"
        )
