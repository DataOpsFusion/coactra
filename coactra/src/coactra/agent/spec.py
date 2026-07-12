"""The canonical declarative description of one Coactra agent."""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass, field
from typing import Any

from coactra.agent.skills import normalize_skills
from coactra.scope import Scope

__all__ = ["AgentSpec"]


@dataclass(frozen=True, slots=True)
class AgentSpec:
    """Carry one agent's identity, routing, scope, and capabilities together."""

    name: str
    model: Any | None = None
    model_capability: str | None = None
    instructions: str | None = None
    scope: Scope | None = None
    tools: tuple[Any, ...] = ()
    skills: Any = ()
    memory: Any = None
    workspace: Any = None
    runtime: Any | None = None
    api_base: str | None = None
    api_key: str | None = None
    gateway: str | None = None
    auth: Any = None
    expose: bool = False
    peers: tuple[Any, ...] = ()
    registry: Any | None = None
    tracer: Any | None = None
    defaults: Mapping[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        if not isinstance(self.name, str) or not self.name:
            raise ValueError("AgentSpec.name must be a non-empty string")
        object.__setattr__(self, "tools", tuple(self.tools or ()))
        object.__setattr__(self, "peers", tuple(self.peers or ()))
        raw_skills = list(self.skills) if isinstance(self.skills, tuple) else self.skills
        object.__setattr__(self, "skills", tuple(normalize_skills(raw_skills)))
        object.__setattr__(self, "defaults", dict(self.defaults))
