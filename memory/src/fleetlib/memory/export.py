"""Lossy export with capability negotiation, provenance, and an honest report.

export() NEVER promises lossless conversion. It intersects the source's and target's
declared Capability sets; everything the source has but the target lacks is recorded in
ExportReport.dropped_capabilities with a human-readable warning. Items still move (their
content + provenance survive), but features the target cannot represent are explicitly
reported as dropped/degraded — not silently lost.
"""

from __future__ import annotations

from pydantic import BaseModel, Field

from fleetlib.memory.backend import MemoryBackend
from fleetlib.memory.capabilities import Capability
from fleetlib.memory.scope import Scope


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


def export(source: MemoryBackend, target: MemoryBackend, *, scope: Scope) -> ExportReport:
    src_caps = source.capabilities()
    dst_caps = target.capabilities()
    dropped = src_caps - dst_caps

    src_name = type(source).__name__
    dst_name = type(target).__name__

    # Deep-copy before mutating: dump() returns the source's own MemoryItem objects.
    # Mutating/ingesting them in place would alias source and target state and corrupt
    # the source's provenance. Copy, then stamp lineage on the copy.
    moved = []
    for item in source.dump(scope):
        copy = item.model_copy(deep=True)
        copy.provenance.exported_from = item.provenance.source_backend
        moved.append(copy)
    written = target.ingest(moved, scope)

    warnings = [
        f"target {dst_name} cannot represent {cap.name}; that feature was dropped"
        for cap in sorted(dropped, key=lambda c: c.name)
    ]
    return ExportReport(
        transferred=len(written),
        source_backend=src_name,
        target_backend=dst_name,
        dropped_capabilities=dropped,
        warnings=warnings,
    )
