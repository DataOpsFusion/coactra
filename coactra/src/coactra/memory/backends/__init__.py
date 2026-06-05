"""Backend adapters behind the ``MemoryBackend`` Protocol.

``InProcessBackend`` is the fully-offline default. ``Mem0Backend`` / ``GraphitiBackend``
wrap real engines and import them lazily — importing this subpackage never requires the
optional extras; only constructing an engine-backed backend does.
"""

from coactra.memory.backends.base import MemoryBackend
from coactra.memory.backends.inprocess import InProcessBackend

__all__ = ["MemoryBackend", "InProcessBackend"]
