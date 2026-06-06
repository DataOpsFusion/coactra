"""coactra.agent — scoped agent composition and policy facade.

The stable root API exposes the agent facade, local domain types, policy/identity
Protocols, and composition helpers. Test fakes, A2A server helpers, and internal data
structures live in their concrete submodules.
"""

from __future__ import annotations

import warnings
from importlib import import_module
from typing import Any

from coactra._version import distribution_version
from coactra.agent.agent import Agent
from coactra.agent.collaboration import (
    A2ATransportPort,
    AgentRef,
    AsyncA2ATransportPort,
    AsyncNullTransport,
    AsyncPolicyGatedCollaborator,
    AllowSameTenant,
    CollaborationDenied,
    CollaborationPolicy,
    NullTransport,
    PolicyGatedCollaborator,
)
from coactra.agent.conformance import TokenExchangeReport, check_token_exchanger_contract
from coactra.agent.domain import (
    DelegationGrant,
    ExchangedIdentity,
    Hop,
    Scope,
    ToolSpec,
    TokenPassthroughError,
)
from coactra.agent.errors import AgentError
from coactra.agent.factory import make_agent
from coactra.agent.identity import (
    AsyncTokenExchanger,
    AsyncTokenExchangerAdapter,
    CachedAsyncTokenExchanger,
    InProcessExchanger,
    TokenExchanger,
)
from coactra.agent.mounting import (
    ConflictPolicy,
    MCPServerPort,
    MountConflictError,
    MountRegistry,
    NamespaceByMountId,
    RejectOnConflict,
)
from coactra.agent.ports import (
    AIPort,
    MemoryPort,
    OrganizationPort,
    WorkflowPort,
    WorkspacePort,
    WorkPort,
)
from coactra.agent.routing import TenantAgentRouter

__all__ = [
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
]

__version__ = distribution_version()

_COMPAT_EXPORTS: dict[str, tuple[str, str]] = {
    "FakeAI": ("coactra.agent.ports", "FakeAI"),
    "FakeMemory": ("coactra.agent.ports", "FakeMemory"),
    "FakeWorkspace": ("coactra.agent.ports", "FakeWorkspace"),
    "FakeWorkflow": ("coactra.agent.ports", "FakeWorkflow"),
    "FakeOrganization": ("coactra.agent.ports", "FakeOrganization"),
    "FakeWork": ("coactra.agent.ports", "FakeWork"),
    "ToolTrie": ("coactra.agent.mounting", "ToolTrie"),
    "build_a2a_app": ("coactra.agent.adapters.a2a_server", "build_a2a_app"),
    "make_a2a_executor": ("coactra.agent.adapters.a2a_server", "make_a2a_executor"),
    "A2AInboundRequest": ("coactra.agent.adapters.a2a_server", "A2AInboundRequest"),
    "A2ARequestVerifier": ("coactra.agent.adapters.a2a_server", "A2ARequestVerifier"),
}


def __getattr__(name: str) -> Any:
    target = _COMPAT_EXPORTS.get(name)
    if target is None:
        raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
    module_name, attr_name = target
    warnings.warn(
        f"coactra.agent.{name} is deprecated; import {attr_name} from {module_name} instead",
        DeprecationWarning,
        stacklevel=2,
    )
    return getattr(import_module(module_name), attr_name)
