from fleetlib.memory import Capability, InProcessBackend, MemoryEvent, Scope

SCOPE = Scope(tenant_id="acme", namespace="agent:1")


def test_learn_stores_items_with_provenance():
    be = InProcessBackend()
    items = be.learn(["dark mode preferred", MemoryEvent(content="deploy ok")], SCOPE)
    assert len(items) == 2
    assert all(i.provenance.source_backend == "inprocess" for i in items)
    assert {i.content for i in be.dump(SCOPE)} == {"dark mode preferred", "deploy ok"}


def test_learn_dedups_identical_content_in_scope():
    be = InProcessBackend()
    be.learn(["same lesson"], SCOPE)
    be.learn(["same lesson"], SCOPE)
    assert len(be.dump(SCOPE)) == 1


def test_capabilities_are_store_and_lexical():
    assert InProcessBackend().capabilities() == {
        Capability.STORE,
        Capability.LEXICAL_RECALL,
        Capability.PROVENANCE,
    }
