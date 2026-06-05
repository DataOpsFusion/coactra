"""Scope-routed agent construction for tenant-silo deployments."""
from __future__ import annotations

from collections.abc import Callable

from coactra._routing import TenantRouter
from coactra.agent.agent import Agent
from coactra.agent.domain import Scope


class TenantAgentRouter:
    """Build and cache an agent runtime per tenant-qualified scope.

    Unlike the sibling routers, an agent is keyed by a whole ``Scope`` (tenant_id +
    namespace), not a bare tenant-id string, so this wraps :class:`coactra._routing.
    TenantRouter` rather than subclassing it: the generic does the lazy build-once cache
    keyed on the frozen, hashable ``Scope``, while the wrapped factory enforces that the
    built runtime actually carries the requested scope (so a drifting factory raises
    before anything is cached).
    """

    def __init__(self, factory: Callable[[Scope], Agent]) -> None:
        def build(scope: Scope) -> Agent:
            agent = factory(scope)
            if agent.scope != scope:
                raise ValueError("agent factory returned a runtime for a different scope")
            return agent

        self._router: TenantRouter[Agent] = TenantRouter(build)

    def for_scope(self, scope: Scope) -> Agent:
        return self._router.for_tenant(scope)
