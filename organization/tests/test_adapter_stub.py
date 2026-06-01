import pytest

from fleetlib.organization.adapters.neo4j import Neo4jOrgStore
from fleetlib.organization.errors import MissingExtraError


def test_neo4j_stub_raises_until_extra_lands():
    with pytest.raises(MissingExtraError, match="neo4j"):
        Neo4jOrgStore(uri="bolt://localhost:7687")
