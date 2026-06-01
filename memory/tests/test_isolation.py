from coactra.memory import Scope
from coactra.memory.backends.inprocess import InProcessBackend

ACME = Scope(tenant="acme", agent="shared")
GLOBEX = Scope(tenant="globex", agent="shared")
ACME_OTHER = Scope(tenant="acme", agent="agent2")


async def test_tenant_cannot_read_other_tenants_items():
    be = InProcessBackend()
    await be.remember(["acme secret"], ACME)
    await be.remember(["globex secret"], GLOBEX)

    assert {r.text for r in await be.dump(ACME)} == {"acme secret"}
    assert {r.text for r in await be.dump(GLOBEX)} == {"globex secret"}
    hits = await be.recall("secret", GLOBEX)
    assert hits[0].text == "globex secret"


async def test_agents_isolate_within_a_tenant():
    be = InProcessBackend()
    await be.remember(["agent1 note"], ACME)
    assert await be.dump(ACME_OTHER) == []
