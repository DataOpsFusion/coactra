from fleetlib.memory import Capability


def test_vocabulary_is_stable():
    # Stability matters: adapters and exports negotiate against these exact names.
    names = {c.name for c in Capability}
    assert names == {
        "STORE",
        "LEXICAL_RECALL",
        "VECTOR_EMBEDDING",
        "GRAPH_EDGES",
        "MEMORY_BLOCK",
        "TEMPORAL",
        "PROVENANCE",
    }


def test_capabilities_support_set_algebra():
    source = {Capability.STORE, Capability.GRAPH_EDGES, Capability.PROVENANCE}
    target = {Capability.STORE, Capability.VECTOR_EMBEDDING, Capability.PROVENANCE}
    dropped = source - target
    assert dropped == {Capability.GRAPH_EDGES}
