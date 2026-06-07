import importlib.metadata

import pytest

import coactra.agent as a

_REMOVED_AGENT_FACTORY = "make" + "_agent"


def test_version_matches_distribution_metadata():
    assert a.__version__ == importlib.metadata.version("coactra")


def test_public_surface_is_stable_root_api():
    expected = {
        "__version__",
        # errors
        "AgentError",
        # domain
        "Scope",
        "AgentRef",
        "DelegationGrant",
        "ExchangedIdentity",
        "Hop",
        "TokenPassthroughError",
        # identity
        "TokenExchanger",
        "AsyncTokenExchanger",
        "AsyncTokenExchangerAdapter",
        "CachedAsyncTokenExchanger",
        "TokenExchangeReport",
        "check_token_exchanger_contract",
        "InProcessExchanger",
        # async collaboration
        "CollaborationPolicy",
        "AllowSameTenant",
        "AsyncA2ATransportPort",
        "AsyncNullTransport",
        "AsyncPolicyGatedCollaborator",
        "CollaborationDenied",
        "RemotePeer",
        "FleetEntry",
        "FleetRegistry",
        "InMemoryFleetRegistry",
        # agent facade exports
        "Agent",
        "Run",
        "RunResult",
        "Event",
        "Assistant",
        "Thinking",
        "ToolCall",
        "ToolResult",
        "Usage",
        "Status",
        "AgentRuntimePort",
        "PydanticAIRuntime",
        "mcp",
    }
    assert set(a.__all__) == expected
    for name in expected:
        assert hasattr(a, name), name
    # cut names must not appear
    assert _REMOVED_AGENT_FACTORY not in a.__all__
    assert "TenantAgentRouter" not in a.__all__
    assert "ToolSpec" not in a.__all__
    assert "MCPServerPort" not in a.__all__
    assert "MountRegistry" not in a.__all__
    assert "AIPort" not in a.__all__
    assert "MemoryPort" not in a.__all__
    assert "A2ATransportPort" not in a.__all__
    assert "NullTransport" not in a.__all__
    assert "PolicyGatedCollaborator" not in a.__all__


def test_old_agent_root_a2a_helpers_are_removed():
    for name in [
        "build_a2a_app",
        "make_a2a_executor",
        "A2AInboundRequest",
        "A2ARequestVerifier",
    ]:
        with pytest.raises(AttributeError):
            getattr(a, name)


def test_removed_names_raise_attribute_error():
    with pytest.raises(AttributeError):
        _ = a.FakeAI
    with pytest.raises(AttributeError):
        _ = a.ToolTrie
    with pytest.raises(AttributeError):
        getattr(a, _REMOVED_AGENT_FACTORY)
