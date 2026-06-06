"""coactra — top-level namespace.

Lazy PEP 562 exports so that ``import coactra`` does NOT pull pydantic-ai.
Heavy symbols are resolved on first attribute access.
"""
from __future__ import annotations

from importlib import import_module
from typing import Any

__all__ = ["Agent", "Run", "StaticToken", "oidc"]

_SDK_EXPORTS = frozenset({"Agent", "Run"})
_AUTH_EXPORTS = frozenset({"StaticToken", "oidc"})
_LAZY_EXPORTS = _SDK_EXPORTS | _AUTH_EXPORTS


def __getattr__(name: str) -> Any:
    if name not in _LAZY_EXPORTS:
        raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
    if name in _AUTH_EXPORTS:
        auth = import_module("coactra.agent.sdk.auth")
        return getattr(auth, name)
    sdk = import_module("coactra.agent.sdk")
    return getattr(sdk, name)
