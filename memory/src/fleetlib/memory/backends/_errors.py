"""Shared error for backends whose engine dependency is an optional extra."""

from __future__ import annotations


class MissingExtraError(RuntimeError):
    """Raised when a backend is used but its optional engine extra isn't installed."""

    def __init__(self, extra: str) -> None:
        super().__init__(
            f"this backend requires the optional '{extra}' extra; "
            f"install with: pip install fleetlib-memory[{extra}]"
        )
        self.extra = extra
