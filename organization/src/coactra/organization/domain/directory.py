"""Domain value objects for optional directory metadata."""
from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class PolicyReference:
    """Versioned reference to a policy owned by another subsystem."""

    name: str
    version: int = 1
    target: str = ""
