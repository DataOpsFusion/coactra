from fleetlib.ai.models import ReasoningTrace
from fleetlib.ai.store import InMemoryStore


def _trace(id, vec, succ=0, fail=0):
    t = ReasoningTrace(id=id, problem=id, reasoning="r", embedding=vec)
    t.successes, t.failures = succ, fail
    return t


def test_tenant_isolation():
    s = InMemoryStore()
    s.put("tenant-a", _trace("t1", [1.0, 0.0]))
    # tenant-b sees nothing
    assert s.search("tenant-b", [1.0, 0.0], k=5, min_quality=0.0) == []
    assert s.get("tenant-b", "t1") is None
    assert s.get("tenant-a", "t1") is not None


def test_search_is_bounded_by_k():
    s = InMemoryStore()
    for i in range(10):
        s.put("a", _trace(f"t{i}", [1.0, 0.0], succ=5))
    hits = s.search("a", [1.0, 0.0], k=3, min_quality=0.0)
    assert len(hits) == 3


def test_search_filters_low_quality():
    s = InMemoryStore()
    s.put("a", _trace("good", [1.0, 0.0], succ=9, fail=0))   # quality ~0.91
    s.put("a", _trace("bad", [1.0, 0.0], succ=0, fail=9))    # quality ~0.09
    hits = s.search("a", [1.0, 0.0], k=5, min_quality=0.5)
    ids = [t.id for t, _ in hits]
    assert ids == ["good"]


def test_search_orders_by_similarity():
    s = InMemoryStore()
    s.put("a", _trace("near", [1.0, 0.0], succ=5))
    s.put("a", _trace("far", [0.0, 1.0], succ=5))
    hits = s.search("a", [1.0, 0.1], k=5, min_quality=0.0)
    assert hits[0][0].id == "near"
