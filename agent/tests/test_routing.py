import pytest

from coactra.agent import Scope, TenantAgentRouter, make_agent


def test_agent_router_builds_once_per_tenant_qualified_scope():
    built = []
    router = TenantAgentRouter(lambda scope: built.append(scope.key) or make_agent(scope=scope))
    acme = Scope(tenant_id="acme", namespace="agent:builder")
    globex = Scope(tenant_id="globex", namespace="agent:builder")
    assert router.for_scope(acme) is router.for_scope(acme)
    assert router.for_scope(globex).scope == globex
    assert built == [acme.key, globex.key]


def test_agent_router_rejects_factory_scope_drift():
    router = TenantAgentRouter(lambda scope: make_agent(scope=Scope(tenant_id="wrong")))
    with pytest.raises(ValueError, match="different scope"):
        router.for_scope(Scope(tenant_id="acme"))
