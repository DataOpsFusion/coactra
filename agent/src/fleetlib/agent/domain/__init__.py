"""domain/ — plain value types, no behavior, no I/O, no sibling imports.

Scope, AgentRef, ToolSpec, DelegationGrant, the immutable actor-chain Hop, and
ExchangedIdentity. Every other layer builds on these.
"""

from fleetlib.agent.domain.identity import (
    DelegationGrant,
    ExchangedIdentity,
    Hop,
    TokenPassthroughError,
)
from fleetlib.agent.domain.refs import AgentRef, as_ref
from fleetlib.agent.domain.scope import Scope
from fleetlib.agent.domain.tools import ToolSpec

__all__ = [
    "Scope",
    "ToolSpec",
    "AgentRef",
    "as_ref",
    "DelegationGrant",
    "ExchangedIdentity",
    "Hop",
    "TokenPassthroughError",
]
