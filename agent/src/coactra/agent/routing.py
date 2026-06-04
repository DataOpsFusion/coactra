"""Scope-routed agent construction for tenant-silo deployments."""
from __future__ import annotations

from collections.abc import Callable

from coactra.agent.agent import Agent
from coactra.agent.domain import Scope


class TenantAgentRouter:
    """Build and cache an agent runtime per tenant-qualified scope."""

    def __init__(self, factory: Callable[[Scope], Agent]) -> None:
        self._factory = factory
        self._agents: dict[str, Agent] = {}

    def for_scope(self, scope: Scope) -> Agent:
        agent = self._agents.get(scope.key)
        if agent is None:
            agent = self._factory(scope)
            if agent.scope != scope:
                raise ValueError("agent factory returned a runtime for a different scope")
            self._agents[scope.key] = agent
        return agent
