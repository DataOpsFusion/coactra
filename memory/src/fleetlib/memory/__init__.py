"""fleetlib.memory — backend-neutral memory connector SPI.

Learns from CONVERSATION (summaries / lessons), recalls later, and exports learning
into any memory/RAG backend. export() is LOSSY by design: it negotiates capabilities,
preserves provenance, and reports every dropped or degraded feature. It never promises
lossless conversion.
"""

from fleetlib.memory.backend import MemoryBackend
from fleetlib.memory.capabilities import Capability
from fleetlib.memory.export import ExportReport, export
from fleetlib.memory.inprocess import InProcessBackend
from fleetlib.memory.models import MemoryEvent, MemoryItem, Provenance
from fleetlib.memory.scope import Scope

__all__ = [
    "__version__",
    "Scope",
    "MemoryEvent",
    "MemoryItem",
    "Provenance",
    "Capability",
    "MemoryBackend",
    "InProcessBackend",
    "ExportReport",
    "export",
]

__version__ = "0.1.0"
