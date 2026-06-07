"""Shared error for backends whose engine dependency is an optional extra."""

from __future__ import annotations

from coactra.errors import MissingExtraError

__all__ = ["MissingExtraError"]
