"""coactra — top-level namespace.

Lazy PEP 562 exports so that ``import coactra`` does NOT pull pydantic-ai.
Heavy symbols are resolved on first attribute access.
"""
from __future__ import annotations

from importlib import import_module
from typing import Any

__all__ = ["Agent", "Run", "Skill", "StaticToken", "Team", "Workflow", "oidc", "serve_agent", "step"]

_SDK_EXPORTS = frozenset({"Agent", "Run"})
_AUTH_EXPORTS = frozenset({"StaticToken", "oidc"})
_SKILLS_EXPORTS = frozenset({"Skill"})
_TEAM_EXPORTS = frozenset({"Team"})
_WORKFLOW_EXPORTS = frozenset({"Workflow", "step"})
_SERVE_EXPORTS = frozenset({"serve_agent"})
_LAZY_EXPORTS = (
    _SDK_EXPORTS | _AUTH_EXPORTS | _SKILLS_EXPORTS | _TEAM_EXPORTS | _WORKFLOW_EXPORTS | _SERVE_EXPORTS
)


def __getattr__(name: str) -> Any:
    if name not in _LAZY_EXPORTS:
        raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
    if name in _AUTH_EXPORTS:
        auth = import_module("coactra.agent.auth")
        return getattr(auth, name)
    if name in _SKILLS_EXPORTS:
        skills = import_module("coactra.agent.skills")
        return getattr(skills, name)
    if name in _TEAM_EXPORTS:
        team = import_module("coactra.agent.team")
        return getattr(team, name)
    if name in _WORKFLOW_EXPORTS:
        workflow = import_module("coactra.workflow")
        return getattr(workflow, name)
    if name in _SERVE_EXPORTS:
        serve = import_module("coactra.agent.serve")
        return getattr(serve, name)
    sdk = import_module("coactra.agent")
    return getattr(sdk, name)
