"""make_agent — composition root that wires ports, mounts, and collaboration."""

from __future__ import annotations

from coactra.agent.agent import Agent
from coactra.agent.collaboration import (
    A2ATransportPort,
    AllowSameTenant,
    CollaborationPolicy,
    NullTransport,
    PolicyGatedCollaborator,
)
from coactra.agent.domain import Scope
from coactra.agent.identity import InProcessExchanger, TokenExchanger
from coactra.agent.mounting import ConflictPolicy, MCPServerPort, MountRegistry
from coactra.agent.ports import (
    AIPort,
    FakeAI,
    FakeMemory,
    FakeOrganization,
    FakeWorkflow,
    FakeWorkspace,
    FakeWork,
    MemoryPort,
    OrganizationPort,
    WorkflowPort,
    WorkspacePort,
    WorkPort,
)


def make_agent(
    *,
    scope: Scope,
    me: str | None = None,
    ai: AIPort | None = None,
    memory: MemoryPort | None = None,
    workspace: WorkspacePort | None = None,
    workflow: WorkflowPort | None = None,
    organization: OrganizationPort | None = None,
    work: WorkPort | None = None,
    mcp: dict[str, MCPServerPort] | None = None,
    transport: A2ATransportPort | None = None,
    exchanger: TokenExchanger | None = None,
    policy: CollaborationPolicy | None = None,
    conflict_policy: ConflictPolicy | None = None,
) -> Agent:
    """Wire a fully-formed ``Agent``; every dependency defaults to an in-process fake."""
    me = me if me is not None else scope.namespace

    ai = ai or FakeAI()
    memory = memory or FakeMemory()
    workspace = workspace or FakeWorkspace(scope=scope)
    workflow = workflow or FakeWorkflow()
    organization = organization or FakeOrganization()
    work = work or FakeWork()
    exchanger = exchanger or InProcessExchanger()
    policy = policy or AllowSameTenant()
    transport = transport or NullTransport()

    mounts = MountRegistry(scope=scope, conflict_policy=conflict_policy)
    if mcp:
        for mount_id, server in mcp.items():
            mounts.stage(mount_id, server)

    collaborator = PolicyGatedCollaborator(
        transport=transport, policy=policy, scope=scope, me=me
    )

    return Agent(
        scope=scope,
        me=me,
        ai=ai,
        memory=memory,
        workspace=workspace,
        workflow=workflow,
        organization=organization,
        work=work,
        exchanger=exchanger,
        mounts=mounts,
        collaborator=collaborator,
        policy=policy,
    )
