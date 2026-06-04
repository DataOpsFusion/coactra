from coactra.organization import OrgStore, SqliteOrgStore, Tenant, TenantOrgStoreRouter


def test_org_router_binds_one_physical_store_per_tenant():
    built = []

    def factory(tenant_id):
        built.append(tenant_id)
        return SqliteOrgStore()

    router = TenantOrgStoreRouter(factory)
    assert isinstance(router, OrgStore)
    router.add_tenant(Tenant(tenant_id="acme"))
    router.add_tenant(Tenant(tenant_id="globex"))
    assert router.members("acme") == []
    assert router.members("globex") == []
    assert built == ["acme", "globex"]
