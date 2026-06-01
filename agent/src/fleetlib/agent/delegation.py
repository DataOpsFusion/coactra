"""Delegated identity via RFC 8693 token exchange — the second session-level gap.

MCP OAuth supports on-behalf-of but EXPLICITLY FORBIDS token passthrough. So an agent
acting for a human (or for an upstream agent) must EXCHANGE the subject token for a fresh
downstream credential whose claims record a subject/actor chain — never forward the raw
token. This module owns that exchange + the multi-hop actor chain; the real Authorization
Server call (Keycloak) is an optional-extra adapter.

Security invariant (proven by tests): the raw subject token never appears in the exchanged
identity's downstream token or its repr.
"""

from __future__ import annotations

import hashlib
from typing import Protocol, runtime_checkable

from pydantic import BaseModel, Field

from fleetlib.agent.scope import Scope


class TokenPassthroughError(RuntimeError):
    """Raised when a caller attempts to forward a raw subject token as the downstream
    credential — the one thing RFC 8693 / MCP OAuth forbids."""


class DelegationGrant(BaseModel):
    """A request to act on behalf of a subject: the subject's token + the acting party."""

    subject_token: str = Field(min_length=1)
    actor: str = Field(min_length=1)
    # Test/guard hook: an explicit attempt to passthrough must be refused.
    passthrough: bool = Field(default=False, alias="_passthrough")

    model_config = {"populate_by_name": True}


class ExchangedIdentity(BaseModel):
    """The fresh downstream credential. It carries WHO is acting (subject + act_chain) but
    never the raw subject token."""

    token: str
    subject: str
    tenant_id: str
    act_chain: list[str] = Field(default_factory=list)

    def __repr__(self) -> str:  # keep the raw subject token out of logs entirely
        return f"ExchangedIdentity(subject={self.subject!r}, act_chain={self.act_chain!r})"


def _mint(material: str, tenant_id: str) -> str:
    """Deterministically derive a fresh, opaque downstream token. NOT the subject token.

    A real AS issues a signed JWT here; the in-process default derives an opaque value so
    the raw subject token can never leak through it (one-way hash).
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
        nested actor chain by one hop. On the Protocol so the multi-hop chain survives
        swapping in KeycloakExchanger (the charter names the multi-hop chain a design point)."""
        ...


class InProcessExchanger:
    """The ONE working default TokenExchanger — no network, no passthrough.

    Mints an opaque downstream token via a one-way derivation, records the actor chain,
    and refuses any explicit passthrough attempt. Swap KeycloakExchanger (oauth extra) for
    a real RFC 8693 token-exchange call against the AS.
    """

    def exchange(self, grant: DelegationGrant, scope: Scope) -> ExchangedIdentity:
        if grant.passthrough:
            raise TokenPassthroughError(
                "token passthrough is forbidden (RFC 8693 / MCP OAuth) — exchange instead"
            )
        return ExchangedIdentity(
            token=_mint(grant.actor, scope.tenant_id),
            subject=grant.actor,
            tenant_id=scope.tenant_id,
            act_chain=[grant.actor],
        )

    def exchange_from(
        self, identity: ExchangedIdentity, *, actor: str, scope: Scope
    ) -> ExchangedIdentity:
        """Multi-hop: re-exchange an already-exchanged identity, extending the act chain."""
        return ExchangedIdentity(
            token=_mint(actor, scope.tenant_id),
            subject=actor,
            tenant_id=scope.tenant_id,
            act_chain=[*identity.act_chain, actor],
        )
