from coactra.ai import InMemoryStore, TenantReasoningStoreRouter
from coactra.ai.protocols import ReasoningStore
from coactra.ai.replay.models import ReasoningTrace


def test_reasoning_store_router_binds_one_store_per_tenant():
    built = []

    def factory(tenant):
        built.append(tenant)
        return InMemoryStore()

    router = TenantReasoningStoreRouter(factory)
    assert isinstance(router, ReasoningStore)
    trace = ReasoningTrace(id="trace-1", problem="x", reasoning="y", embedding=[1.0])
    router.put("acme", trace)
    assert router.get("acme", trace.id) == trace
    assert router.get("globex", trace.id) is None
    assert built == ["acme", "globex"]
