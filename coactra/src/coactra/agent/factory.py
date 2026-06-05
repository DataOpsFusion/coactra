"""make_agent — the composition root.

The ONE place anything is instantiated. It wires the six ports (defaulting to faithful
in-process fakes), the token exchanger, the mount registry, and the policy-gated
collaborator, then hands the fully-built collaborators to the `Agent` (which constructs
nothing itself). Swap any port/transport/exchanger/policy for a real adapter to go live;
the default path needs only pydantic and zero siblings.

`me` (the agent's self-identity for collaboration) is NOT in the spec's signature, so it
is DERIVED from `scope.namespace` by default (matching the v0.1 convention where
namespace == agent id, e.g. `agent:platform`). Pass `me=` to override.
"""

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
    """Wire a fully-formed `Agent`. Every dependency defaults to an in-process fake.

    Args:
      scope: the mandatory tenant/namespace key threaded through every subsystem.
      me: self-identity for collaboration; defaults to `scope.namespace`.
      ai/memory/workspace/workflow/organization/work: the six capability PORTS (fakes by default).
      mcp: optional initial mounts (`{mount_id: server}`) staged at construction — they
           remain INVISIBLE until the first `begin_turn()`, like any mid-session mount.
      transport: the A2A wire behind the collaboration gate (NullTransport by default).
      exchanger: the RFC-8693 token exchanger (InProcessExchanger by default).
      policy: the CollaborationPolicy (AllowSameTenant by default).
      conflict_policy: tool-name conflict resolution (NamespaceByMountId by default).
    """
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

    # ONE policy instance, shared by Agent.can_talk() and the gated collaborator (no drift).
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
