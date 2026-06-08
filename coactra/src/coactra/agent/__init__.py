"""coactra.agent — scoped agent composition and policy facade.

The stable root API exposes local domain types, policy/identity protocols, and the async
collaboration stack. Adapters (outbound a2a/keycloak), SDK, and internal data structures
live in their concrete submodules.
"""

from __future__ import annotations

from importlib import import_module
from typing import Any

from coactra._version import distribution_version
from coactra.agent.collaboration import (
    AgentRef,
    AllowSameTenant,
    AsyncA2ATransportPort,
    AsyncNullTransport,
    AsyncPolicyGatedCollaborator,
    CollaborationDenied,
    CollaborationPolicy,
)
from coactra.agent.conformance import TokenExchangeReport, check_token_exchanger_contract
from coactra.agent.domain import (
    DelegationGrant,
    ExchangedIdentity,
    Hop,
    Scope,
    TokenPassthroughError,
)
from coactra.agent.domain.tools import MCPServer, mcp
from coactra.agent.errors import AgentError
from coactra.agent.events import (
    Assistant,
    Event,
    RunResult,
    Status,
    Thinking,
    ToolCall,
    ToolResult,
    Usage,
)
from coactra.agent.identity import (
    AsyncTokenExchanger,
    AsyncTokenExchangerAdapter,
    CachedAsyncTokenExchanger,
    InProcessExchanger,
    TokenExchanger,
)

_LAZY_EXPORTS: dict[str, tuple[str, str]] = {
    "Agent": ("coactra.agent.facade", "Agent"),
    "Run": ("coactra.agent.run", "Run"),
    "RemotePeer": ("coactra.agent.peers", "RemotePeer"),
    "FleetEntry": ("coactra.agent.registry", "FleetEntry"),
    "FleetRegistry": ("coactra.agent.registry", "FleetRegistry"),
    "InMemoryFleetRegistry": ("coactra.agent.registry", "InMemoryFleetRegistry"),
    "AgentRuntimePort": ("coactra.agent.ports", "AgentRuntimePort"),
    "PydanticAIRuntime": ("coactra.agent.runtime", "PydanticAIRuntime"),
}

__all__ = [
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
    # agent SDK
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
    "MCPServer",
    "mcp",
]

__version__ = distribution_version()


def __getattr__(name: str) -> Any:
    target = _LAZY_EXPORTS.get(name)
    if target is None:
        raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
    module_name, attr_name = target
    return getattr(import_module(module_name), attr_name)
