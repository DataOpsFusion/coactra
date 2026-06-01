import asyncio

import coactra.agent as a


def test_version_is_v2():
    assert a.__version__ == "0.2.0"


def test_public_surface_is_complete():
    expected = {
        "__version__",
        # domain
        "Scope",
        "ToolSpec",
        "AgentRef",
        "DelegationGrant",
        "ExchangedIdentity",
        "Hop",
        "TokenPassthroughError",
        # mounting (DSA)
        "MCPServerPort",
        "ConflictPolicy",
        "NamespaceByMountId",
        "RejectOnConflict",
        "MountConflictError",
        "MountRegistry",
        "ToolTrie",
        # identity (DSA)
        "TokenExchanger",
        "InProcessExchanger",
        # collaboration
        "CollaborationPolicy",
        "AllowSameTenant",
        "AgentRef",
        "A2ATransportPort",
        "NullTransport",
        "PolicyGatedCollaborator",
        "CollaborationDenied",
        # ports + fakes
        "AIPort",
        "MemoryPort",
        "WorkspacePort",
        "WorkflowPort",
        "OrganizationPort",
        "WorkPort",
        "FakeAI",
        "FakeMemory",
        "FakeWorkspace",
        "FakeWorkflow",
        "FakeOrganization",
        "FakeWork",
        "FakeOrgNode",
        "FakeMember",
        # facade + composition root
        "Agent",
        "make_agent",
    }
    assert expected <= set(a.__all__)
    for name in expected:
        assert hasattr(a, name), name


def test_removed_v01_names_are_gone():
    # API genuinely moved in v0.2: the v0.1 sync MemoryPort.learn / AIPort.complete /
    # OrganizationPort.escalation_chain surfaces are gone — the fakes no longer expose them.
    assert not hasattr(a.FakeAI(), "complete")
    assert not hasattr(a.FakeMemory(), "learn")
    assert not hasattr(a.FakeOrganization(), "escalation_chain")


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
    # Load the REAL coactra.workflow.runtime.handlers module DIRECTLY by file path. handlers.py is
    # leaf-importable (it imports only typing + pydantic), so this gives us the ACTUAL
    # Protocols the inter-lib contract is defined against WITHOUT importing coactra.workflow
    # (which pulls langgraph via langgraph_engine). The test can therefore never drift from
    # the real workflow contract — if workflow renames/reshapes a seam, this breaks.
    import importlib.util
    from pathlib import Path

    here = Path(__file__).resolve()
    # repo layout: <repo>/agent/tests/test_public_api.py  ->  <repo>/workflow/src/...
    repo_root = here.parents[2]
    handlers_path = (
        repo_root / "workflow" / "src" / "coactra" / "workflow" / "runtime" / "handlers.py"
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
    # The agent's collaborator STRUCTURALLY satisfies coactra.workflow's Collaborator /
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
