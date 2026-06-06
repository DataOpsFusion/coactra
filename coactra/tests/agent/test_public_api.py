import importlib.metadata

import pytest

import coactra.agent as a


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
    }
    assert set(a.__all__) == expected
    for name in expected:
        assert hasattr(a, name), name
    # cut names must not appear
    assert "Agent" not in a.__all__
    assert "make_agent" not in a.__all__
    assert "TenantAgentRouter" not in a.__all__
    assert "ToolSpec" not in a.__all__
    assert "MCPServerPort" not in a.__all__
    assert "MountRegistry" not in a.__all__
    assert "AIPort" not in a.__all__
    assert "MemoryPort" not in a.__all__
    assert "A2ATransportPort" not in a.__all__
    assert "NullTransport" not in a.__all__
    assert "PolicyGatedCollaborator" not in a.__all__


def test_deprecated_agent_root_compat_imports_warn():
    with pytest.warns(DeprecationWarning, match="coactra.agent.build_a2a_app is deprecated"):
        build_a2a_app = a.build_a2a_app

    assert build_a2a_app.__name__ == "build_a2a_app"


def test_removed_names_raise_attribute_error():
    with pytest.raises(AttributeError):
        _ = a.FakeAI
    with pytest.raises(AttributeError):
        _ = a.ToolTrie
    with pytest.raises(AttributeError):
        _ = a.Agent
    with pytest.raises(AttributeError):
        _ = a.make_agent
