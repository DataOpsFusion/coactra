from fleetlib.memory import Capability


def test_vocabulary_is_stable():
    # Adapters and exports negotiate against these exact names.
    names = {c.name for c in Capability}
    assert {
        "STORE",
        "LEXICAL_RECALL",
        "VECTOR_EMBEDDING",
        "GRAPH_EDGES",
        "TEMPORAL",
        "PROVENANCE",
    } <= names


def test_capabilities_support_set_algebra():
    source = {Capability.STORE, Capability.GRAPH_EDGES, Capability.PROVENANCE}
    target = {Capability.STORE, Capability.VECTOR_EMBEDDING, Capability.PROVENANCE}
    assert source - target == {Capability.GRAPH_EDGES}
