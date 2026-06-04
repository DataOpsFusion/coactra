"""Plain, framework-agnostic value types — the public vocabulary.

These are the ONLY shapes that cross the public boundary. A backend never returns a
mem0/graphiti object; it maps engine results into a ``Recollection``. ``Scope`` is the
tenant-scoped key threaded through every call, and it maps down to each engine's own
scoping primitive (mem0 ``user_id``/``agent_id``/``run_id``; graphiti ``group_id``).

There is NO engine type, ORM, or pydantic-from-engine leak here by design.
"""

from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, Field, field_validator

# A learnable conversational unit handed to remember(). Either a plain string
# ("the build broke on the linter step") or an OpenAI-style chat message dict
# ({"role": "user", "content": "..."}). Engines that auto-extract (mem0/graphiti)
# consume the messages directly; the in-process backend flattens to text.
MemoryEvent = str | dict[str, str]


class Scope(BaseModel):
    """Immutable, hashable tenant key.

    ``tenant`` is mandatory and is ALWAYS encoded into the engine scoping key, so a
    recall can never reach across tenants. ``namespace`` optionally names a reusable
    shared partition such as ``"department/infrastructure"`` or ``"company"``.
    ``agent`` and ``session`` optionally narrow the partition further.

    Existing three-slot keys are preserved when ``namespace`` is omitted. Namespaced
    scopes use a distinct five-slot encoding, so adding shared memory does not move or
    collide with existing per-agent memory.
    """

    model_config = {"frozen": True}

    tenant: str = Field(min_length=1)
    namespace: str | None = None
    agent: str | None = None
    session: str | None = None

    @field_validator("tenant", "namespace", "agent", "session")
    @classmethod
    def _no_reserved_chars(cls, v: str | None, info) -> str | None:
        """Keep the encoded key injective: reject the delimiter, the absent-field
        placeholder, and an empty narrowing field.

        ``key`` (and every backend that builds a scope key, e.g. graphiti's
        ``group_id``) uses ':' delimiters and '*' placeholders. If a field could
        contain ':' two distinct scopes could collapse to one key (a cross-tenant
        collision); '*' would alias the absent-field slot; and an empty agent/session
        would also alias the absent slot. Forbidding all three keeps the map one-to-one.
        """
        if v is None:  # absent narrowing field — fine
            return v
        if ":" in v:
            raise ValueError(
                f"Scope.{info.field_name} may not contain ':' (the scope-key delimiter); "
                f"got {v!r}. ':' would let two distinct scopes share one engine key."
            )
        if v == "*":
            raise ValueError(
                f"Scope.{info.field_name} may not be '*' (reserved absent-field placeholder); got {v!r}."
            )
        if info.field_name != "tenant" and v == "":
            raise ValueError(
                f"Scope.{info.field_name} may not be empty; use None to leave it unset."
            )
        return v

    @property
    def key(self) -> str:
        """A stable, collision-resistant string key (tenant always first)."""
        if self.namespace is not None:
            return ":".join(
                [
                    self.tenant,
                    "@",
                    self.namespace,
                    self.agent or "*",
                    self.session or "*",
                ]
            )
        return ":".join([self.tenant, self.agent or "*", self.session or "*"])


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
