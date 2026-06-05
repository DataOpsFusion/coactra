from coactra.directory import PolicyRef, Tenant


def test_add_and_get_current_policy_version(store):
    store.add_tenant(Tenant(tenant_id="acme"))
    store.add_policy_ref("acme", PolicyRef(tenant_id="acme", name="retention", version=1, target="logs"))
    store.add_policy_ref("acme", PolicyRef(tenant_id="acme", name="retention", version=2, target="logs"))

    current = store.policy_ref("acme", "retention")
    assert current.version == 2  # current = highest version


def test_get_specific_policy_version(store):
    store.add_tenant(Tenant(tenant_id="acme"))
    store.add_policy_ref("acme", PolicyRef(tenant_id="acme", name="retention", version=1, target="logs"))
    store.add_policy_ref("acme", PolicyRef(tenant_id="acme", name="retention", version=2, target="logs"))

    v1 = store.policy_ref("acme", "retention", version=1)
    assert v1.version == 1


def test_policy_refs_are_tenant_scoped(store):
    store.add_tenant(Tenant(tenant_id="acme"))
    store.add_tenant(Tenant(tenant_id="globex"))
    store.add_policy_ref("globex", PolicyRef(tenant_id="globex", name="retention", version=5, target="logs"))
    assert store.policy_ref("acme", "retention") is None
