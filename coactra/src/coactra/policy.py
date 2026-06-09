"""Shared policy contract for scoped, governed Coactra actions."""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass, field
from enum import StrEnum
from typing import Any, Protocol, runtime_checkable

from coactra.scope import Scope


class DecisionOutcome(StrEnum):
    allow = "allow"
    deny = "deny"
    requires_approval = "requires_approval"


@dataclass(frozen=True, slots=True)
class Decision:
    outcome: DecisionOutcome
    reason: str = ""
    source: str = "unknown"
    metadata: dict[str, Any] = field(default_factory=dict)

    @property
    def allowed(self) -> bool:
        return self.outcome is DecisionOutcome.allow


@dataclass(frozen=True, slots=True)
class PolicyRequest:
    principal: str
    action: str
    resource: str
    scope: Scope
    component: str
    context: dict[str, Any] = field(default_factory=dict)


@runtime_checkable
class Policy(Protocol):
    async def check(self, request: PolicyRequest) -> Decision: ...


class _StaticPolicy:
    def __init__(self, outcome: DecisionOutcome, *, source: str, reason: str = "") -> None:
        self._outcome = outcome
        self._source = source
        self._reason = reason

    async def check(self, request: PolicyRequest) -> Decision:
        return Decision(outcome=self._outcome, source=self._source, reason=self._reason)


class _ObservedPolicy:
    def __init__(self, *, default: DecisionOutcome, source: str = "observed") -> None:
        self._default = default
        self._source = source
        self.decisions: list[PolicyRequest] = []

    async def check(self, request: PolicyRequest) -> Decision:
        self.decisions.append(request)
        return Decision(outcome=self._default, source=self._source)


class _AuthorizerBackedPolicy:
    def __init__(
        self,
        authorizer: Any,
        *,
        access_resolver: Callable[[PolicyRequest], Any],
        source: str = "authorizer",
    ) -> None:
        self._authorizer = authorizer
        self._access_resolver = access_resolver
        self._source = source

    async def check(self, request: PolicyRequest) -> Decision:
        access = self._access_resolver(request)
        result = await self._authorizer.allowed(request.principal, access, request.scope)
        if isinstance(result, Decision):
            return result
        return Decision(
            outcome=DecisionOutcome.allow if result else DecisionOutcome.deny,
            source=self._source,
        )


def permissive() -> Policy:
    return _StaticPolicy(DecisionOutcome.allow, source="permissive")


def default_deny() -> Policy:
    return _StaticPolicy(DecisionOutcome.deny, source="default_deny")


def observed(*, default: DecisionOutcome = DecisionOutcome.allow) -> _ObservedPolicy:
    return _ObservedPolicy(default=default)


def from_authorizer(
    authorizer: Any,
    *,
    access_resolver: Callable[[PolicyRequest], Any] | None = None,
    source: str = "authorizer",
) -> Policy:
    resolver = access_resolver or (lambda request: request.action)
    return _AuthorizerBackedPolicy(authorizer, access_resolver=resolver, source=source)


Policy.permissive = staticmethod(permissive)  # type: ignore[attr-defined]
Policy.default_deny = staticmethod(default_deny)  # type: ignore[attr-defined]
Policy.observed = staticmethod(observed)  # type: ignore[attr-defined]
Policy.from_authorizer = staticmethod(from_authorizer)  # type: ignore[attr-defined]


__all__ = [
    "Decision",
    "DecisionOutcome",
    "Policy",
    "PolicyRequest",
]
