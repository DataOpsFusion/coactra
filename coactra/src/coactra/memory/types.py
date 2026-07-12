"""Plain, framework-agnostic value types — the public vocabulary.

These are the ONLY shapes that cross the public boundary. A backend never returns a
mem0/graphiti object; it maps engine results into a ``Recollection``. The canonical
``coactra.scope.Scope`` is threaded through every call and maps down to each engine's
own scoping primitive (mem0 ``user_id``/``agent_id``/``run_id``; graphiti ``group_id``).

There is NO engine type, ORM, or pydantic-from-engine leak here by design.
"""

from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, Field

# A learnable conversational unit handed to remember(). Either a plain string
# ("the build broke on the linter step") or an OpenAI-style chat message dict
# ({"role": "user", "content": "..."}). Engines that auto-extract (mem0/graphiti)
# consume the messages directly; the in-process backend flattens to text.
MemoryEvent = str | dict[str, str]


class Recollection(BaseModel):
    """A single recalled memory — the plain return type of ``recall``/``dump``.

    NEVER a mem0/graphiti object. ``score`` is recall-time relevance (0.0 on ``dump``,
    which has no query). ``source_id`` is the engine's own id for the item, so a caller
    can correlate without holding an engine handle. Lineage for export lives in
    ``metadata`` (``source_backend`` / ``exported_from``).
    """

    text: str
    score: float = 0.0
    source_id: str = ""
    when: datetime | None = None
    metadata: dict = Field(default_factory=dict)
