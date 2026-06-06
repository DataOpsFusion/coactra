"""coactra.memory — a thin, clean connector to long-term memory engines.

mem0 and Graphiti already do extraction + consolidation + recall, so this package is a
small, framework-agnostic facade over one async ``MemoryBackend`` Protocol — not a
reimplemented store. Two headline verbs: ``remember`` and ``recall``. ``export`` (lossy,
capability-negotiated) stays off the headline. Returns are always plain ``Recollection``
objects; no mem0/graphiti type ever leaks across the boundary.

    from coactra.memory import Memory, make_backend, Scope

    mem = Memory(backend=make_backend("inprocess"))   # "mem0" | "graphiti" too
    scope = Scope(tenant="acme", agent="builder")
    await mem.remember(["the build broke on the linter step"], scope=scope)
    hits = await mem.recall("why did the build break", scope=scope, k=5)

    # blocking bridge for sync callers / scripts:
    Memory(backend=make_backend("inprocess")).sync.recall("q", scope=scope)
"""

from coactra._version import distribution_version

from coactra.memory.authorization import (
    AllowListMemoryAuthorizer,
    AuthorizedMemory,
    MemoryAccess,
    MemoryAccessDenied,
    MemoryAuthorizer,
)
from coactra.memory.backends.base import MemoryBackend
from coactra.memory.capabilities import Capability
from coactra.memory.conformance import MemoryBackendReport, check_memory_backend_contract
from coactra.memory.export import ExportReport, export
from coactra.memory.facade import Memory
from coactra.memory.factory import make_backend
from coactra.memory.routing import TenantMemoryBackendRouter
from coactra.memory.types import MemoryEvent, Recollection, Scope

__all__ = [
    "__version__",
    "Memory",
    "make_backend",
    "Scope",
    "Recollection",
    "MemoryEvent",
    "MemoryBackend",
    "MemoryAccess",
    "MemoryAccessDenied",
    "MemoryAuthorizer",
    "AllowListMemoryAuthorizer",
    "AuthorizedMemory",
    "Capability",
    "MemoryBackendReport",
    "check_memory_backend_contract",
    "ExportReport",
    "export",
    "TenantMemoryBackendRouter",
]

__version__ = distribution_version()
