"""Lossy export with capability negotiation, provenance, and an honest report.

``export`` NEVER promises lossless conversion. It intersects the source's and target's
declared ``Capability`` sets; everything the source has but the target lacks is recorded
in ``ExportReport.dropped_capabilities`` with a human-readable warning. Items still move
(their text + lineage survive in ``Recollection.metadata``), but features the target
cannot represent are explicitly reported as dropped — not silently lost.

This stays OFF the headline surface: callers reach it via ``Memory.export(to=...)``.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from pydantic import BaseModel, Field

from fleetlib.memory.capabilities import Capability
from fleetlib.memory.types import Scope

if TYPE_CHECKING:  # avoid runtime import cycle (base imports ExportReport name only)
    from fleetlib.memory.backends.base import MemoryBackend


class ExportReport(BaseModel):
    """The honest record of a (lossy) export."""

    transferred: int = 0
    source_backend: str = ""
    target_backend: str = ""
    dropped_capabilities: set[Capability] = Field(default_factory=set)
    warnings: list[str] = Field(default_factory=list)

    @property
    def lossless(self) -> bool:
        """True only when no source capability was dropped at the target."""
        return not self.dropped_capabilities


async def export(
    source: "MemoryBackend", target: "MemoryBackend", *, scope: Scope
) -> ExportReport:
    """Move a scope's recollections from ``source`` into ``target``, lossily and honestly."""
    src_caps = await source.capabilities()
    dst_caps = await target.capabilities()
    dropped = src_caps - dst_caps

    src_name = type(source).__name__
    dst_name = type(target).__name__

    # Copy before stamping lineage: dump() may return the source's own objects, and we
    # must not mutate source state. Stamp exported_from on the copy only.
    moved = []
    for rec in await source.dump(scope):
        copy = rec.model_copy(deep=True)
        meta = dict(copy.metadata)
        meta["exported_from"] = meta.get("source_backend", src_name)
        copy = copy.model_copy(update={"metadata": meta})
        moved.append(copy)

    ingest_report = await target.ingest(moved, scope)

    warnings = [
        f"target {dst_name} cannot represent {cap.name}; that feature was dropped"
        for cap in sorted(dropped, key=lambda c: c.name)
    ]
    return ExportReport(
        transferred=ingest_report.transferred,
        source_backend=src_name,
        target_backend=dst_name,
        dropped_capabilities=dropped,
        warnings=warnings,
    )
