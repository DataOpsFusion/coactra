"""domain/ — plain value types, no behavior, no I/O, no sibling imports.

Scope, AgentRef, ToolSpec, DelegationGrant, the immutable actor-chain Hop, and
ExchangedIdentity. Every other layer builds on these.
"""

from coactra.agent.domain.identity import (
    DelegationGrant,
    ExchangedIdentity,
    Hop,
    TokenPassthroughError,
)
from coactra.agent.domain.refs import AgentRef, as_ref
from coactra.agent.domain.tools import ToolSpec
from coactra.scope import Scope

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
