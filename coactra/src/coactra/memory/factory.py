"""make_backend — the DI selection point.

The facade NEVER builds a backend inline; callers pass one in. This factory is the one
place a name maps to a concrete backend. Unknown name → ``ValueError``; a known name
whose engine extra is missing → ``MissingExtraError`` (raised from the backend ctor).
"""

from __future__ import annotations

from typing import Any

from coactra.memory.backends.base import MemoryBackend

_NAMES = ("inprocess", "mem0", "graphiti")


def make_backend(name: str, **config: Any) -> MemoryBackend:
    """Construct a backend by name. ``**config`` is forwarded to the backend ctor."""
    if name == "inprocess":
        from coactra.memory.backends.inprocess import InProcessBackend

        return InProcessBackend(**config)
    if name == "mem0":
        from coactra.memory.backends.mem0 import Mem0Backend

        return Mem0Backend(**config)
    if name == "graphiti":
        from coactra.memory.backends.graphiti import GraphitiBackend

        return GraphitiBackend(**config)
    raise ValueError(f"unknown backend {name!r}; choose one of {', '.join(_NAMES)}")
