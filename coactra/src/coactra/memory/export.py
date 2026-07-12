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

from coactra.memory.capabilities import Capability
from coactra.scope import Scope

if TYPE_CHECKING:
    from coactra.memory.backends.base import MemoryExporter


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

    @classmethod
    def from_ingest(cls, backend: object, *, transferred: int) -> ExportReport:
        """Target-side report a backend's ``ingest`` returns.

        Records only what the target knows: how many items it wrote and its own name.
        ``source_backend`` is left blank here on purpose — ``export`` stamps it from the
        actual source once both ends are known.
        """
        return cls(transferred=transferred, target_backend=type(backend).__name__)


async def export(source: MemoryExporter, target: MemoryExporter, *, scope: Scope) -> ExportReport:
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
