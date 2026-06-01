import fleetlib.agent as a


def test_public_surface_is_complete():
    expected = {
        "__version__",
        "Scope",
        "ToolSpec",
        # mounting
        "MCPServerPort",
        "ConflictPolicy",
        "NamespaceByMountId",
        "MountConflictError",
        "MountRegistry",
        # delegation
        "DelegationGrant",
        "ExchangedIdentity",
        "TokenExchanger",
        "InProcessExchanger",
        "TokenPassthroughError",
        # collaboration
        "CollaborationPolicy",
        "AllowSameTenant",
        "AgentRef",
        "A2ATransportPort",
        "PolicyGatedCollaborator",
        "CollaborationDenied",
        # ports + fakes
        "AIPort",
        "MemoryPort",
        "WorkspacePort",
        "WorkflowPort",
        "OrganizationPort",
        "FakeAI",
        "FakeMemory",
        "FakeWorkspace",
        "FakeWorkflow",
        "FakeOrganization",
        # composition root
        "Agent",
    }
    assert expected <= set(a.__all__)
    for name in expected:
        assert hasattr(a, name), name


def test_end_to_end_composition():
    scope = a.Scope(tenant_id="acme", namespace="agent:platform")
    agent = a.Agent(scope=scope, me="agent:platform")

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
    agent.memory("deploy ok")
    assert agent.recall("deploy") == ["deploy ok"]
    assert agent.run_procedure("deploy")["ran"] is True


def test_collaborator_is_workflow_runcontext_ready():
    # The agent's collaborator structurally satisfies workflow's Collaborator/EscalationRouter:
    # it has .ask(agent, question, state) and .route(escalation, chain).
    agent = a.Agent(scope=a.Scope(tenant_id="acme"), me="agent:a")
    c = agent.collaborator
    assert hasattr(c, "ask") and hasattr(c, "route")
