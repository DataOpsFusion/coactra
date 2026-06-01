"""fleetlib.agent — the runtime that wires the five sibling capabilities into a working
agent, as a thin composition/POLICY layer ABOVE mature protocols (it does NOT fork them).

It builds only the three session-level gaps the research verdict identified:
  1. mid-session MCP mounting exposed on the next safe model turn (+ conflict + cache
     invalidation),
  2. delegated identity via RFC 8693 token exchange (subject/actor chains) — NEVER token
     passthrough,
  3. collaboration policy over A2A (who may talk to whom, when) — with tenant-qualified,
     deniable targets (AgentRef carries its own tenant, so cross-tenant talk is deniable).

The five siblings (ai/memory/workspace/workflow/organization) are consumed through narrow
local port Protocols, never by importing their internals. Every default is in-process and
unit-testable; the real SDKs/transports are optional-extra stubs.
"""

from fleetlib.agent.agent import Agent
from fleetlib.agent.collaboration import (
    A2ATransportPort,
    AgentRef,
    AllowSameTenant,
    CollaborationDenied,
    CollaborationPolicy,
    PolicyGatedCollaborator,
)
from fleetlib.agent.delegation import (
    DelegationGrant,
    ExchangedIdentity,
    InProcessExchanger,
    TokenExchanger,
    TokenPassthroughError,
)
from fleetlib.agent.mounting import (
    ConflictPolicy,
    MCPServerPort,
    MountConflictError,
    MountRegistry,
    NamespaceByMountId,
)
from fleetlib.agent.ports import (
    AIPort,
    FakeAI,
    FakeMemory,
    FakeOrganization,
    FakeWorkflow,
    FakeWorkspace,
    MemoryPort,
    OrganizationPort,
    WorkflowPort,
    WorkspacePort,
)
from fleetlib.agent.scope import Scope
from fleetlib.agent.tools import ToolSpec

__all__ = [
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
]

__version__ = "0.1.0"
