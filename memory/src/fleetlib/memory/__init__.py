"""fleetlib.memory — a thin, clean connector to long-term memory engines.

mem0 and Graphiti already do extraction + consolidation + recall, so this package is a
small, framework-agnostic facade over one async ``MemoryBackend`` Protocol — not a
reimplemented store. Two headline verbs: ``remember`` and ``recall``. ``export`` (lossy,
capability-negotiated) stays off the headline. Returns are always plain ``Recollection``
objects; no mem0/graphiti type ever leaks across the boundary.

    from fleetlib.memory import Memory, make_backend, Scope

    mem = Memory(backend=make_backend("inprocess"))   # "mem0" | "graphiti" too
    scope = Scope(tenant="acme", agent="builder")
    await mem.remember(["the build broke on the linter step"], scope=scope)
    hits = await mem.recall("why did the build break", scope=scope, k=5)

    # blocking bridge for sync callers / scripts:
    Memory(backend=make_backend("inprocess")).sync.recall("q", scope=scope)
"""

from fleetlib.memory.backends.base import MemoryBackend
from fleetlib.memory.capabilities import Capability
from fleetlib.memory.export import ExportReport, export
from fleetlib.memory.facade import Memory
from fleetlib.memory.factory import make_backend
from fleetlib.memory.types import MemoryEvent, Recollection, Scope

__all__ = [
    "__version__",
    "Memory",
    "make_backend",
    "Scope",
    "Recollection",
    "MemoryEvent",
    "MemoryBackend",
    "Capability",
    "ExportReport",
    "export",
]

__version__ = "0.2.0"
