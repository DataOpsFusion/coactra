"""Policy-gated model routing."""

from __future__ import annotations

from collections.abc import Iterable
from typing import Any

from coactra.policy import DecisionOutcome, Policy, PolicyRequest
from coactra.scope import Scope

from .models import ModelRoute


class ModelResolver:
    """Resolve requested model capabilities to concrete routes."""

    def __init__(self, routes: Iterable[ModelRoute] | None = None) -> None:
        self._routes: dict[str, ModelRoute] = {}
        for route in routes or ():
            self.register(route)

    def register(self, route: ModelRoute) -> ModelRoute:
        self._routes[route.capability] = route
        return route

    @property
    def capabilities(self) -> tuple[str, ...]:
        """Registered capability names, in registration order."""
        return tuple(self._routes)

    def route(self, capability: str) -> ModelRoute | None:
        return self._routes.get(capability)

    async def resolve(
        self,
        capability: str,
        *,
        principal: str,
        scope: Scope,
        policy: Policy,
        context: dict[str, Any] | None = None,
    ) -> ModelRoute:
        route = self.route(capability)
        if route is None:
            raise KeyError(f"unknown model capability {capability!r}")

        decision = await policy.check(
            PolicyRequest(
                principal=principal,
                action="model.use",
                resource=f"model_capability:{capability}",
                scope=scope,
                component="model",
                context={
                    "capability": capability,
                    "profile": route.profile.name,
                    **(context or {}),
                },
            )
        )
        if decision.outcome is not DecisionOutcome.allow:
            raise PermissionError(
                f"model capability {capability!r} denied with outcome {decision.outcome}"
            )
        return route
