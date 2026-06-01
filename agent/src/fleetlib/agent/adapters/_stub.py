"""Shared helper for optional-extra adapter stubs."""

from __future__ import annotations


class MissingExtraError(RuntimeError):
    """Raised when an optional-extra adapter is used before its extra/impl exist."""


def require_extra(extra: str) -> None:
    raise MissingExtraError(
        f"adapter requires the optional '{extra}' extra and a real implementation; "
        f"install with: pip install fleetlib-agent[{extra}] (stub not yet implemented)"
    )
