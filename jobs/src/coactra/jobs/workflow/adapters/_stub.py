"""Shared helper for optional-extra engine stubs."""

from __future__ import annotations


class MissingExtraError(RuntimeError):
    """Raised when an optional-extra engine is used before its extra/impl exist."""


def require_extra(extra: str) -> None:
    raise MissingExtraError(
        f"engine requires the optional '{extra}' extra and a real implementation; "
        f"install with: pip install coactra-jobs[{extra}] (stub not yet implemented)"
    )
