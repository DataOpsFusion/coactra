import asyncio
import importlib.metadata

import pytest

import coactra.agent as a
from coactra.agent.ports import FakeAI, FakeMemory, FakeOrganization


def test_version_matches_distribution_metadata():
    assert a.__version__ == importlib.metadata.version("coactra")


def test_public_surface_is_stable_root_api():
    expected = {
        "__version__",
        # errors
        "AgentError",
        # domain
        "Scope",
        "ToolSpec",
        "AgentRef",
        "DelegationGrant",
        "ExchangedIdentity",
        "Hop",
        "TokenPassthroughError",
        # mounting
        "MCPServerPort",
        "ConflictPolicy",
        "NamespaceByMountId",
        "RejectOnConflict",
        "MountConflictError",
        "MountRegistry",
        # identity
        "TokenExchanger",
        "AsyncTokenExchanger",
        "AsyncTokenExchangerAdapter",
        "CachedAsyncTokenExchanger",
        "TokenExchangeReport",
        "check_token_exchanger_contract",
        "InProcessExchanger",
        # collaboration
        "CollaborationPolicy",
        "AllowSameTenant",
        "AgentRef",
        "A2ATransportPort",
        "AsyncA2ATransportPort",
        "NullTransport",
        "AsyncNullTransport",
        "PolicyGatedCollaborator",
        "AsyncPolicyGatedCollaborator",
        "CollaborationDenied",
        # ports
        "AIPort",
        "MemoryPort",
        "WorkspacePort",
        "WorkflowPort",
        "OrganizationPort",
        "WorkPort",
        # facade + composition root
        "Agent",
        "make_agent",
        "TenantAgentRouter",
    }
    assert set(a.__all__) == expected
    for name in expected:
        assert hasattr(a, name), name
    assert "FakeAI" not in a.__all__
    assert "ToolTrie" not in a.__all__
    assert "build_a2a_app" not in a.__all__


def test_deprecated_agent_root_compat_imports_warn():
    with pytest.warns(DeprecationWarning, match="coactra.agent.FakeAI is deprecated"):
        fake_ai = a.FakeAI
    with pytest.warns(DeprecationWarning, match="coactra.agent.ToolTrie is deprecated"):
        tool_trie = a.ToolTrie
    with pytest.warns(DeprecationWarning, match="coactra.agent.build_a2a_app is deprecated"):
        build_a2a_app = a.build_a2a_app

    assert fake_ai is FakeAI
    assert tool_trie.__name__ == "ToolTrie"
    assert build_a2a_app.__name__ == "build_a2a_app"


def test_removed_v01_names_are_gone():
    # API genuinely moved in v0.2: the v0.1 sync MemoryPort.learn / AIPort.complete /
    # OrganizationPort.escalation_chain surfaces are gone — the fakes no longer expose them.
    assert not hasattr(FakeAI(), "complete")
    assert not hasattr(FakeMemory(), "learn")
    assert not hasattr(FakeOrganization(), "escalation_chain")


def test_end_to_end_composition():
    agent = a.make_agent(scope=a.Scope(tenant_id="acme", namespace="agent:platform"))

    # (1) mid-session mount -> not visible -> begin_turn -> visible
    class Srv:
        def list_tools(self):
            return ["read_file"]

    agent.mount_mcp("fs", Srv(), effective="next_turn")
    assert agent.tools() == []
    agent.begin_turn()
    assert agent.tools() == ["fs.read_file"]

    # (2) delegated identity — no passthrough
    ident = agent.act_on_behalf_of(
        a.DelegationGrant(subject_token="HUMAN-SECRET", actor="agent:platform")
    )
    assert "HUMAN-SECRET" not in ident.token

    # (3) collaboration policy
    assert agent.can_talk("agent:security") is True

    # sibling delegation — thin shims call the ports
    async def scenario():
        await agent.remember(["deploy ok"])
        return await agent.recall("deploy")

    hits = asyncio.run(scenario())
    assert [r["text"] for r in hits] == ["deploy ok"]
    assert agent.run_procedure("deploy")["ran"] is True


def _load_workflow_handlers():
    # Load the REAL coactra.jobs.workflow.runtime.handlers module DIRECTLY by file path. handlers.py is
    # leaf-importable (it imports only typing + pydantic), so this gives us the ACTUAL
    # Protocols the inter-lib contract is defined against WITHOUT importing coactra.jobs.workflow
    # (without pulling an optional backend). The test can therefore never drift from
    # the real workflow contract — if workflow renames/reshapes a seam, this breaks.
    import importlib.util
    from pathlib import Path

    here = Path(__file__).resolve()
    # repo layout: <repo>/coactra/tests/agent/test_public_api.py  ->  <repo>/coactra/src/coactra/jobs/workflow/...
    pkg_root = here.parents[2]
    handlers_path = (
        pkg_root / "src" / "coactra" / "jobs" / "workflow" / "runtime" / "handlers.py"
    )
    assert handlers_path.is_file(), (
        f"real workflow handlers not found at {handlers_path}"
    )

    spec = importlib.util.spec_from_file_location(
        "_wf_handlers_under_test", handlers_path
    )
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def test_collaborator_is_workflow_runcontext_ready():
    # The agent's collaborator STRUCTURALLY satisfies coactra.jobs.workflow's Collaborator /
    # EscalationRouter Protocols. We assert against the REAL Protocols loaded by file path
    # (no langgraph import) so this can't drift from workflow's actual contract.
    import inspect

    wf = _load_workflow_handlers()

    agent = a.make_agent(scope=a.Scope(tenant_id="acme"))
    c = agent.collaborator

    # (1) runtime_checkable isinstance proves the METHODS are present.
    assert isinstance(c, wf.Collaborator)
    assert isinstance(c, wf.EscalationRouter)

    # (2) isinstance only checks presence, not shape — so also assert the parameter NAMES
    # match the real Protocol method signatures (excluding self). This catches a real
    # rename/reorder/add drift while tolerating the deliberate first-param widening in
    # PolicyGatedCollaborator.ask (str -> str | AgentRef), which keeps the same param names.
    def _param_names(fn):
        return [p for p in inspect.signature(fn).parameters if p != "self"]

    assert _param_names(c.ask) == _param_names(wf.Collaborator.ask)
    assert _param_names(c.route) == _param_names(wf.EscalationRouter.route)

    # exercise the EscalationRouter seam POSITIONALLY, the way a workflow run calls it
    class Esc:
        reason = "stuck"

    assert c.route(Esc(), ["manager", "human"]) == "human"
