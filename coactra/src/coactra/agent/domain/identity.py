"""Delegated-identity value types — RFC 8693 token exchange.

The actor chain is an **immutable linked list of subject->actor hops** (a cons list): each
hop points at the one before it (`prev`), so extending the chain allocates a single new
head that SHARES the existing tail. No hop is ever mutated; an older `ExchangedIdentity`
keeps the exact chain structure it was minted with, even after a further delegation hop.

Security invariant (proven by tests): the raw subject token never appears in an exchanged
identity's downstream token or its repr — only WHO is acting is recorded, never the
subject's bearer credential.
"""

from __future__ import annotations

from collections.abc import Iterator

from pydantic import BaseModel, Field

from coactra.errors import SecurityError


class TokenPassthroughError(SecurityError):
    """Raised when a caller attempts to forward a raw subject token as the downstream
    credential — the one thing RFC 8693 / MCP OAuth forbids."""


class DelegationGrant(BaseModel):
    """A request to act on behalf of a subject: the subject's token + the acting party."""

    subject_token: str = Field(min_length=1)
    actor: str = Field(min_length=1)
    # Optional pre-existing application delegation path, such as a host's
    audience: str | None = None
    requested_scopes: tuple[str, ...] = Field(default_factory=tuple)
    # client_credentials + delegation_chain grant model.
    delegation_chain: list[str] = Field(default_factory=list)
    # Test/guard hook: an explicit attempt to passthrough must be refused.
    passthrough: bool = Field(default=False, alias="_passthrough")

    model_config = {"populate_by_name": True}


class Hop(BaseModel):
    """One immutable subject->actor hop in the delegation chain (a cons cell).

    ``prev`` is the hop that precedes this one (None at the head of the chain). The cell is
    frozen, so a chain shares its tail across delegations: ``delegate_further`` allocates a
    single new ``Hop`` whose ``prev`` is the existing head — the prior chain is untouched.
    """

    model_config = {"frozen": True}

    subject: str = Field(min_length=1)
    actor: str = Field(min_length=1)
    prev: Hop | None = None

    def extend(self, *, subject: str, actor: str) -> Hop:
        """Return a NEW head hop appended after this one; this hop is left unchanged."""
        return Hop(subject=subject, actor=actor, prev=self)

    def __iter__(self) -> Iterator[Hop]:
        """Walk the chain oldest-first (root subject -> ... -> this actor)."""
        node: Hop | None = self
        stack: list[Hop] = []
        while node is not None:
            stack.append(node)
            node = node.prev
        yield from reversed(stack)

    def actors(self) -> list[str]:
        """The acting parties oldest-first — the flattened delegation path."""
        return [hop.actor for hop in self]

    @property
    def depth(self) -> int:
        """Number of hops in the chain (>=1)."""
        return len(self.actors())


Hop.model_rebuild()


class ExchangedIdentity(BaseModel):
    """The fresh downstream credential. It carries WHO is acting (the immutable actor
    chain) but never the raw subject token."""

    model_config = {"frozen": True}

    token: str
    subject: str
    tenant_id: str
    chain: Hop

    @property
    def act_chain(self) -> list[str]:
        """The flattened actor path oldest-first (compat view of the linked chain)."""
        return self.chain.actors()

    def __repr__(self) -> str:  # keep the raw subject token out of logs entirely
        return f"ExchangedIdentity(subject={self.subject!r}, act_chain={self.act_chain!r})"
