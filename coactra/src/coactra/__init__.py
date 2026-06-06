"""coactra — top-level namespace.

Lazy PEP 562 exports so that ``import coactra`` does NOT pull pydantic-ai.
Heavy symbols are resolved on first attribute access.
"""
from __future__ import annotations

from importlib import import_module
from typing import Any

__all__ = ["Agent", "Run"]

_LAZY_EXPORTS = frozenset({"Agent", "Run"})


def __getattr__(name: str) -> Any:
    if name not in _LAZY_EXPORTS:
        raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
    sdk = import_module("coactra.agent.sdk")
    return getattr(sdk, name)
