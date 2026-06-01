"""Shared helper for optional-extra adapter stubs."""

from __future__ import annotations


class MissingExtraError(RuntimeError):
    """Raised when an optional-extra backend is used before its extra/impl exist."""


def require_extra(extra: str) -> None:
    raise MissingExtraError(
        f"backend requires the optional '{extra}' extra and a real implementation; "
        f"install with: pip install fleetlib-memory[{extra}] (stub not yet implemented)"
    )
