"""coactra.agent — scoped agent composition and policy facade.

The stable root API exposes local domain types, policy/identity protocols, and the async
collaboration stack. Adapters (a2a/a2a_server/keycloak), SDK, and internal data structures
live in their concrete submodules.
"""

from __future__ import annotations

import warnings
from importlib import import_module
from typing import Any

from coactra._version import distribution_version
from coactra.agent.collaboration import (
    AgentRef,
    AsyncA2ATransportPort,
    AsyncNullTransport,
    AsyncPolicyGatedCollaborator,
    AllowSameTenant,
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
from coactra.agent.errors import AgentError
from coactra.agent.identity import (
    AsyncTokenExchanger,
    AsyncTokenExchangerAdapter,
    CachedAsyncTokenExchanger,
    InProcessExchanger,
    TokenExchanger,
)

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
]

__version__ = distribution_version()

_COMPAT_EXPORTS: dict[str, tuple[str, str]] = {
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
