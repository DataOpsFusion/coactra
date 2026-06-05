import asyncio

import pytest

from coactra.directory import AsyncOrgStore, AsyncPostgresOrgStore, Member, Seat, Tenant


class FakeStore:
    def __init__(self):
        self.tenants = []

    def add_tenant(self, tenant):
        self.tenants.append(tenant)
        return tenant

    def add_member(self, tenant_id, member):
        return member

    def add_seat(self, tenant_id, seat):
        return seat

    def directory(self, tenant_id):
        return {"tenant": tenant_id}

    def owner_of(self, tenant_id, resource_domain):
        return None

    def escalate(self, tenant_id, seat_id):
        return None


def test_async_postgres_facade_satisfies_async_protocol_and_delegates_off_loop():
    inner = FakeStore()
    store = AsyncPostgresOrgStore(store=inner)
    assert isinstance(store, AsyncOrgStore)
    tenant = Tenant(tenant_id="acme")
    assert asyncio.run(store.add_tenant(tenant)) == tenant
    assert asyncio.run(store.directory("acme")) == {"tenant": "acme"}
    assert inner.tenants == [tenant]


def test_async_postgres_facade_requires_postgres_url_without_injected_store():
    with pytest.raises(ValueError, match="postgresql"):
        AsyncPostgresOrgStore("sqlite://")


def test_plain_postgres_url_is_normalized_to_psycopg3(monkeypatch):
    import coactra.directory.repository.async_store as module

    seen = []
    monkeypatch.setattr(module, "make_engine", lambda url: seen.append(url) or object())
    monkeypatch.setattr(module, "SqliteOrgStore", lambda engine: object())
    module.AsyncPostgresOrgStore("postgresql://db.example/org")
    assert seen == ["postgresql+psycopg://db.example/org"]
