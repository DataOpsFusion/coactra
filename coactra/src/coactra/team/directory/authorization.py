"""Backend-neutral authorization decisions.

The directory package owns directory structure and permission references. External
policy engines remain optional adapters behind this narrow async port.
"""

from __future__ import annotations

import uuid
from collections.abc import Iterable
from typing import Any, Protocol, runtime_checkable

from pydantic import BaseModel, Field


class AuthorizationRequest(BaseModel):
    """One subject-action-resource authorization query."""

    subject: str = Field(min_length=1)
    action: str = Field(min_length=1)
    resource: str = Field(min_length=1)
    context: dict[str, Any] = Field(default_factory=dict)


class AuthorizationDecision(BaseModel):
    """Auditable result returned by every authorization adapter."""

    id: str = Field(default_factory=lambda: uuid.uuid4().hex)
    allowed: bool
    source: str = Field(min_length=1)
    reason: str = ""
    metadata: dict[str, Any] = Field(default_factory=dict)


@runtime_checkable
class Authorizer(Protocol):
    """Async authorization SPI suitable for local rules or a remote policy engine."""

    async def check(self, request: AuthorizationRequest) -> AuthorizationDecision:
        """Return an auditable allow or deny decision."""
        ...


class InMemoryAuthorizer:
    """Small default-deny authorizer for local use and deterministic tests."""

    def __init__(
        self,
        grants: Iterable[tuple[str, str, str]] = (),
        *,
        default_allow: bool = False,
    ) -> None:
        self._grants = set(grants)
        self._default_allow = default_allow

    def grant(self, subject: str, action: str, resource: str) -> None:
        self._grants.add((subject, action, resource))

    def revoke(self, subject: str, action: str, resource: str) -> None:
        self._grants.discard((subject, action, resource))

    async def check(self, request: AuthorizationRequest) -> AuthorizationDecision:
        allowed = (
            request.subject,
            request.action,
            request.resource,
        ) in self._grants or self._default_allow
        return AuthorizationDecision(
            allowed=allowed,
            source="inmemory",
            reason="explicit grant" if allowed else "no matching grant",
        )


class AuthorizationDenied(PermissionError):
    """Raised by :func:`require_authorized` for a denied operation."""

    def __init__(self, decision: AuthorizationDecision) -> None:
        self.decision = decision
        super().__init__(decision.reason or "authorization denied")


async def require_authorized(
    authorizer: Authorizer, request: AuthorizationRequest
) -> AuthorizationDecision:
    """Return the decision or raise while retaining its audit identifier."""

    decision = await authorizer.check(request)
    if not decision.allowed:
        raise AuthorizationDenied(decision)
    return decision
