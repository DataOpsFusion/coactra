from fleetlib.memory import InProcessBackend, Scope

ACME = Scope(tenant_id="acme", namespace="shared")
GLOBEX = Scope(tenant_id="globex", namespace="shared")
ACME_OTHER_NS = Scope(tenant_id="acme", namespace="agent:2")


def test_tenant_cannot_read_other_tenants_items():
    be = InProcessBackend()
    be.learn(["acme secret"], ACME)
    be.learn(["globex secret"], GLOBEX)

    assert {i.content for i in be.dump(ACME)} == {"acme secret"}
    assert {i.content for i in be.dump(GLOBEX)} == {"globex secret"}
    assert be.recall("secret", GLOBEX)[0].content == "globex secret"


def test_namespaces_isolate_within_a_tenant():
    be = InProcessBackend()
    be.learn(["ns1 note"], ACME)
    assert be.dump(ACME_OTHER_NS) == []
