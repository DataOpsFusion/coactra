"""Declarative Team specifications."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from coactra.agent.skills import Skill

__all__ = ["TeamAgentSpec"]


@dataclass(frozen=True, slots=True)
class TeamAgentSpec:
    """Declarative config for one agent in a Team."""

    name: str
    model: Any | None = None
    model_capability: str | None = None
    instructions: str | None = None
    tools: tuple[Any, ...] = ()
    runtime: Any | None = None
    api_base: str | None = None
    api_key: str | None = None
    gateway: str | None = None
    auth: Any = None
    memory: Any = None
    workspace: Any = None
    skills: tuple[Skill, ...] = field(default_factory=tuple)
    expose: bool = False
    peers: tuple[Any, ...] = ()
    registry: Any | None = None
    tracer: Any | None = None
    defaults: dict[str, Any] = field(default_factory=dict)
