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
import inspect
import time
from collections.abc import Awaitable, Callable
from typing import Protocol, cast, runtime_checkable

from coactra.agent.domain import Scope
from coactra.agent.domain.identity import (
    DelegationGrant,
    ExchangedIdentity,
    Hop,
    TokenPassthroughError,
)

__all__ = [
    "TokenExchanger",
    "AsyncTokenExchanger",
    "InProcessExchanger",
    "AsyncTokenExchangerAdapter",
    "CachedAsyncTokenExchanger",
    "DelegationGrant",
    "ExchangedIdentity",
    "Hop",
    "TokenPassthroughError",
]


def _mint(material: str, tenant_id: str) -> str:
    """Deterministically derive a fresh, opaque downstream token. NOT the subject token.

    A real AS issues a signed JWT here; the in-process default derives an opaque value via
    a one-way hash, so the raw source token can never leak through it.
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


@runtime_checkable
class AsyncTokenExchanger(Protocol):
    async def exchange(self, grant: DelegationGrant, scope: Scope) -> ExchangedIdentity:
        """Async exchange for service runtimes that should not block an event loop."""
        ...

    async def exchange_from(
        self, identity: ExchangedIdentity, *, actor: str, scope: Scope
    ) -> ExchangedIdentity:
        """Async multi-hop exchange."""
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
            token=_mint(f"{grant.actor}:{grant.subject_token}", scope.tenant_id),
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
            token=_mint(f"{actor}:{identity.token}", scope.tenant_id),
            subject=actor,
            tenant_id=scope.tenant_id,
            chain=head,
        )


class AsyncTokenExchangerAdapter:
    """Expose a synchronous exchanger through the async contract."""

    def __init__(self, exchanger: TokenExchanger) -> None:
        self._exchanger = exchanger

    async def exchange(self, grant: DelegationGrant, scope: Scope) -> ExchangedIdentity:
        return self._exchanger.exchange(grant, scope)

    async def exchange_from(
        self, identity: ExchangedIdentity, *, actor: str, scope: Scope
    ) -> ExchangedIdentity:
        return self._exchanger.exchange_from(identity, actor=actor, scope=scope)


def as_async_exchanger(
    exchanger: AsyncTokenExchanger | TokenExchanger,
) -> AsyncTokenExchanger:
    """Return ``exchanger`` unchanged if it's already async, else wrap the sync one in a
    worker-thread adapter. One place owns the sync-vs-async normalization."""
    if inspect.iscoroutinefunction(exchanger.exchange):
        return exchanger  # type: ignore[return-value]
    return AsyncTokenExchangerAdapter(cast(TokenExchanger, exchanger))


class CachedAsyncTokenExchanger:
    """Cache exchange results by tenant, actor, audience, scopes, and token hash."""

    def __init__(
        self,
        exchanger: AsyncTokenExchanger | TokenExchanger,
        *,
        ttl_seconds: float = 60.0,
        clock: Callable[[], float] = time.monotonic,
    ) -> None:
        self._exchanger: AsyncTokenExchanger = as_async_exchanger(exchanger)
        self._ttl_seconds = ttl_seconds
        self._clock = clock
        self._cache: dict[str, tuple[float, ExchangedIdentity]] = {}

    async def exchange(self, grant: DelegationGrant, scope: Scope) -> ExchangedIdentity:
        return await self._cached(
            self._grant_key(grant, scope),
            lambda: self._exchanger.exchange(grant, scope),
        )

    async def exchange_from(
        self, identity: ExchangedIdentity, *, actor: str, scope: Scope
    ) -> ExchangedIdentity:
        token_hash = hashlib.sha256(identity.token.encode()).hexdigest()
        key = f"from:{scope.tenant_id}:{identity.subject}:{actor}:{token_hash}"
        return await self._cached(
            key,
            lambda: self._exchanger.exchange_from(identity, actor=actor, scope=scope),
        )

    async def _cached(
        self,
        key: str,
        factory: Callable[[], Awaitable[ExchangedIdentity]],
    ) -> ExchangedIdentity:
        now = self._clock()
        cached = self._cache.get(key)
        if cached is not None and cached[0] > now:
            return cached[1]
        identity = await factory()
        self._cache[key] = (now + self._ttl_seconds, identity)
        return identity

    @staticmethod
    def _grant_key(grant: DelegationGrant, scope: Scope) -> str:
        token_hash = hashlib.sha256(grant.subject_token.encode()).hexdigest()
        return ":".join(
            [
                "grant",
                scope.tenant_id,
                grant.actor,
                grant.audience or "",
                ",".join(grant.requested_scopes),
                ",".join(grant.delegation_chain),
                token_hash,
            ]
        )
