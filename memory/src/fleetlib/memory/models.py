"""Memory data models.

MemoryEvent  — raw input ("what happened / what was learned" in a conversation).
MemoryItem   — a stored unit, always carrying Provenance (origin + lineage).
Provenance   — where an item came from; preserved across export so lineage survives
               a lossy backend hop.
"""

from __future__ import annotations

import uuid
from datetime import datetime, timezone
from typing import Literal

from pydantic import BaseModel, Field

MemoryKind = Literal["lesson", "summary", "fact", "preference"]


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


class Provenance(BaseModel):
    """Lineage of a MemoryItem. Set at creation, carried through every export hop."""

    source_backend: str
    created_at: datetime = Field(default_factory=_utcnow)
    exported_from: str | None = None  # backend name an item was exported out of, if any


class MemoryEvent(BaseModel):
    """A learnable conversational event handed to learn()."""

    content: str = Field(min_length=1)
    kind: MemoryKind = "lesson"
    tags: list[str] = Field(default_factory=list)


class MemoryItem(BaseModel):
    """A stored memory unit. Provenance is mandatory — there is no item without lineage."""

    id: str = Field(default_factory=lambda: uuid.uuid4().hex)
    content: str
    kind: MemoryKind
    tags: list[str] = Field(default_factory=list)
    provenance: Provenance

    @classmethod
    def from_event(cls, event: MemoryEvent, *, source_backend: str) -> "MemoryItem":
        return cls(
            content=event.content,
            kind=event.kind,
            tags=list(event.tags),
            provenance=Provenance(source_backend=source_backend),
        )
