"""Delegated identity via RFC 8693 token exchange — the second session-level gap.

MCP OAuth supports on-behalf-of but EXPLICITLY FORBIDS token passthrough. So an agent
acting for a human (or an upstream agent) must EXCHANGE the subject token for a fresh
downstream credential whose claims record the subject->actor chain — never forward the raw
token. This module owns the exchange + the multi-hop chain; the real AS call (Keycloak)
is an optional-extra adapter.

The chain itself is the immutable cons-list `Hop` from `domain.identity` — see that module
for the data structure. Here we only own the exchange MECHANISM and the no-passthrough
guarantee.
"""

from __future__ import annotations

import hashlib
from typing import Protocol, runtime_checkable

from coactra.agent.domain import Scope
from coactra.agent.domain.identity import (
    DelegationGrant,
    ExchangedIdentity,
    Hop,
    TokenPassthroughError,
)

__all__ = [
    "TokenExchanger",
    "InProcessExchanger",
    "DelegationGrant",
    "ExchangedIdentity",
    "Hop",
    "TokenPassthroughError",
]


def _mint(material: str, tenant_id: str) -> str:
    """Deterministically derive a fresh, opaque downstream token. NOT the subject token.

    A real AS issues a signed JWT here; the in-process default derives an opaque value via
    a one-way hash, so the raw subject token can never leak through it.
    """
    digest = hashlib.sha256(f"{tenant_id}:{material}".encode()).hexdigest()
    return f"exch_{digest[:32]}"


@runtime_checkable
class TokenExchanger(Protocol):
    def exchange(self, grant: DelegationGrant, scope: Scope) -> ExchangedIdentity:
        """Exchange a subject token for a fresh on-behalf-of identity (never passthrough)."""
        ...

    def exchange_from(
        self, identity: ExchangedIdentity, *, actor: str, scope: Scope
    ) -> ExchangedIdentity:
        """Multi-hop RFC 8693: re-exchange an already-exchanged identity, extending the
        immutable actor chain by one hop (the prior identity's chain stays untouched). On
        the Protocol so multi-hop survives swapping in a real KeycloakExchanger."""
        ...


class InProcessExchanger:
    """The ONE working default TokenExchanger — no network, no passthrough.

    Mints an opaque downstream token via a one-way derivation, records the immutable actor
    chain, and refuses any explicit passthrough attempt. Swap KeycloakExchanger (oauth
    extra) for a real RFC 8693 token-exchange call against the AS.
    """

    def exchange(self, grant: DelegationGrant, scope: Scope) -> ExchangedIdentity:
        if grant.passthrough:
            raise TokenPassthroughError(
                "token passthrough is forbidden (RFC 8693 / MCP OAuth) — exchange instead"
            )
        # The head hop: the actor acts for the (un-named, token-only) subject. The subject
        # token is consumed here and never stored on the chain or the downstream token.
        head = Hop(subject=grant.actor, actor=grant.actor)
        return ExchangedIdentity(
            token=_mint(grant.actor, scope.tenant_id),
            subject=grant.actor,
            tenant_id=scope.tenant_id,
            chain=head,
        )

    def exchange_from(
        self, identity: ExchangedIdentity, *, actor: str, scope: Scope
    ) -> ExchangedIdentity:
        """Multi-hop: append one hop, SHARING the prior chain's tail (cons)."""
        head = identity.chain.extend(subject=identity.subject, actor=actor)
        return ExchangedIdentity(
            token=_mint(actor, scope.tenant_id),
            subject=actor,
            tenant_id=scope.tenant_id,
            chain=head,
        )
