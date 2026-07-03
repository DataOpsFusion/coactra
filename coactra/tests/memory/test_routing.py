import pytest

from coactra.memory import (
    Capability,
    MemoryReader,
    Scope,
    TenantMemoryRouter,
    make_backend,
)


@pytest.mark.asyncio
async def test_memory_router_binds_one_backend_per_tenant():
    built = []

    def factory(tenant):
        built.append(tenant)
        return make_backend("inprocess")

    router = TenantMemoryRouter(factory)
    assert isinstance(router, MemoryReader)
    acme = Scope(tenant="acme")
    globex = Scope(tenant="globex")
    await router.remember(["acme secret"], acme)
    assert [item.text for item in await router.recall("secret", acme)] == ["acme secret"]
    assert await router.recall("secret", globex) == []
    assert built == ["acme", "globex"]


@pytest.mark.asyncio
async def test_router_capabilities_empty_when_no_backends():
    router = TenantMemoryRouter(lambda _t: make_backend("inprocess"))
    assert await router.capabilities() == set()


@pytest.mark.asyncio
async def test_router_capabilities_intersect_cached_backends():
    class FakeBackend:
        def __init__(self, caps: set[Capability]) -> None:
            self._caps = caps

        async def capabilities(self) -> set[Capability]:
            return set(self._caps)

    caps_by_tenant = {
        "acme": {Capability.STORE, Capability.LEXICAL_RECALL, Capability.PROVENANCE},
        "globex": {Capability.STORE, Capability.PROVENANCE},
    }
    router = TenantMemoryRouter(lambda t: FakeBackend(caps_by_tenant[t]))
    router.for_tenant("acme")
    router.for_tenant("globex")
    # Routers span heterogeneous silos; advertise only universally-supported capabilities.
    assert await router.capabilities() == {Capability.STORE, Capability.PROVENANCE}
