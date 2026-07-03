"""coactra — top-level namespace.

Lazy PEP 562 exports so that ``import coactra`` does NOT pull pydantic-ai.
Heavy symbols are resolved on first attribute access.
"""

from __future__ import annotations

from importlib import import_module
from typing import Any

from coactra._version import distribution_version

__version__ = distribution_version()

__all__ = [
    "Agent",
    "CoactraError",
    "Decision",
    "DecisionOutcome",
    "ErrorCode",
    "MissingExtraError",
    "ModelProfile",
    "ModelResolver",
    "ModelRoute",
    "Policy",
    "PolicyRequest",
    "RemotePeer",
    "Run",
    "Scope",
    "Skill",
    "StaticToken",
    "Team",
    "TeamExtension",
    "ValidationError",
    "Workflow",
    "__version__",
]

_SDK_EXPORTS = frozenset({"Agent", "RemotePeer", "Run"})
_AUTH_EXPORTS = frozenset({"StaticToken"})
_SKILLS_EXPORTS = frozenset({"Skill"})
_SCOPE_EXPORTS = frozenset({"Scope"})
_TEAM_EXPORTS = frozenset({"Team", "TeamExtension"})
_WORKFLOW_EXPORTS = frozenset({"Workflow"})
_MODEL_EXPORTS = frozenset({"ModelProfile", "ModelResolver", "ModelRoute"})
_POLICY_EXPORTS = frozenset({"Policy", "PolicyRequest", "Decision", "DecisionOutcome"})
_ERROR_EXPORTS = frozenset({"CoactraError", "ErrorCode", "MissingExtraError", "ValidationError"})
_VERSION_EXPORTS = frozenset({"__version__"})
_LAZY_EXPORTS = (
    _SDK_EXPORTS
    | _AUTH_EXPORTS
    | _SKILLS_EXPORTS
    | _SCOPE_EXPORTS
    | _TEAM_EXPORTS
    | _WORKFLOW_EXPORTS
    | _MODEL_EXPORTS
    | _POLICY_EXPORTS
    | _ERROR_EXPORTS
    | _VERSION_EXPORTS
)


def __getattr__(name: str) -> Any:
    if name == "__version__":
        return __version__
    if name not in _LAZY_EXPORTS:
        raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
    if name in _AUTH_EXPORTS:
        auth = import_module("coactra.agent.auth")
        return getattr(auth, name)
    if name in _SKILLS_EXPORTS:
        skills = import_module("coactra.agent.skills")
        return getattr(skills, name)
    if name in _SCOPE_EXPORTS:
        scope = import_module("coactra.scope")
        return getattr(scope, name)
    if name in _TEAM_EXPORTS:
        team = import_module("coactra.team")
        return getattr(team, name)
    if name in _WORKFLOW_EXPORTS:
        return getattr(import_module("coactra.agent.workflow"), name)
    if name in _MODEL_EXPORTS:
        model = import_module("coactra.model")
        return getattr(model, name)
    if name in _POLICY_EXPORTS:
        policy = import_module("coactra.policy")
        return getattr(policy, name)
    if name in _ERROR_EXPORTS:
        errors = import_module("coactra.errors")
        return getattr(errors, name)
    sdk = import_module("coactra.agent")
    return getattr(sdk, name)


def __dir__() -> list[str]:
    return sorted(__all__)
