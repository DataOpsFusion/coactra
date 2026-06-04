"""Helpers for optional integration dependencies."""

from __future__ import annotations

from importlib import import_module
from types import ModuleType


class MissingExtraError(ImportError):
    """Raised when an integration is used without its optional dependency."""


def optional_module(module: str, *, extra: str, package: str | None = None) -> ModuleType:
    try:
        return import_module(module)
    except ImportError as exc:
        install = package or extra
        raise MissingExtraError(
            f"{module!r} requires the optional {extra!r} integration; "
            f"install with: pip install coactra-orchestration[{install}]"
        ) from exc
