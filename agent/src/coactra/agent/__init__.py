"""coactra.agent — the runtime that WIRES the six sibling capabilities into a working
agent, as a thin composition/POLICY layer ABOVE mature protocols (it does NOT fork them).

It builds only the three session-level gaps the research verdict identified:
  1. mid-session MCP mounting exposed on the next safe model turn — a prefix-trie tool
     namespace + a pending->active state machine (mounting.py);
  2. delegated identity via RFC 8693 token exchange — an immutable subject->actor chain,
     NEVER token passthrough (identity.py + domain.identity);
  3. collaboration policy over A2A — tenant-qualified, deniable `AgentRef` targets
     (collaboration.py + domain.refs).

The six siblings (ai/memory/workspace/workflow/organization/work) are consumed through narrow
local port Protocols shaped to MIRROR the real sibling facades (ports/), never by importing
their internals. Build one with `make_agent(...)` (factory.py); every default is an
in-process fake, so the package is fully testable with zero siblings installed.

    from coactra.agent import make_agent, Scope, DelegationGrant

    agent = make_agent(scope=Scope(tenant_id="acme", namespace="agent:platform"))
    agent.mount_mcp("fs", my_mcp_server)   # invisible until the next turn
    agent.begin_turn()                     # now agent.tools() == ["fs.read_file", ...]
    ident = agent.act_on_behalf_of(DelegationGrant(subject_token=tok, actor=agent.me))
    reply = agent.talk("agent:security", "is it safe?")   # gated by collaboration policy
"""

from coactra.agent.agent import Agent
from coactra.agent.collaboration import (
    A2ATransportPort,
    AgentRef,
    AllowSameTenant,
    CollaborationDenied,
    CollaborationPolicy,
    NullTransport,
    PolicyGatedCollaborator,
)
from coactra.agent.domain import (
    DelegationGrant,
    ExchangedIdentity,
    Hop,
    Scope,
    ToolSpec,
    TokenPassthroughError,
)
from coactra.agent.factory import make_agent
from coactra.agent.identity import InProcessExchanger, TokenExchanger
from coactra.agent.mounting import (
    ConflictPolicy,
    MCPServerPort,
    MountConflictError,
    MountRegistry,
    NamespaceByMountId,
    RejectOnConflict,
    ToolTrie,
)
from coactra.agent.ports import (
    AIPort,
    FakeAI,
    FakeMember,
    FakeMemory,
    FakeOrganization,
    FakeOrgNode,
    FakeWorkflow,
    FakeWorkspace,
    FakeWork,
    MemoryPort,
    OrganizationPort,
    WorkflowPort,
    WorkspacePort,
    WorkPort,
)

__all__ = [
    "__version__",
    # domain
    "Scope",
    "ToolSpec",
    "AgentRef",
    "DelegationGrant",
    "ExchangedIdentity",
    "Hop",
    "TokenPassthroughError",
    # mounting (DSA: prefix trie + state machine)
    "MCPServerPort",
    "ConflictPolicy",
    "NamespaceByMountId",
    "RejectOnConflict",
    "MountConflictError",
    "MountRegistry",
    "ToolTrie",
    # identity (DSA: immutable actor chain)
    "TokenExchanger",
    "InProcessExchanger",
    # collaboration
    "CollaborationPolicy",
    "AllowSameTenant",
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
]

__version__ = "0.2.0"
