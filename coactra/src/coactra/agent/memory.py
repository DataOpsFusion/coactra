"""coactra.agent.memory — automatic recall/remember connector.

A thin connector around a ``coactra.memory.MemoryBackend``.  coactra never ranks,
embeds, or consolidates — all of that belongs to the backend (graphiti/mem0/inprocess).
This module owns *when* recall/remember happen and enforces the guardrails from
design/2026-06-06-review-refinements.md item 6:

- tenant/scope isolation (threaded through every call)
- max-injected-memory cap  (``max_recall``)
- memory-write policy      (``write_policy``)
- provenance / source      (best-effort: accepted at the call site; the Protocol's
  ``remember(events, scope)`` has no metadata channel, so ``source`` is currently
  noted in the call but not forwarded — attach provenance once a backend exposes it)
"""

from __future__ import annotations

from collections.abc import Callable

from coactra.memory.backends.base import MemoryBackend
from coactra.memory.factory import make_backend as _make_backend
from coactra.memory.types import Scope

# ---------------------------------------------------------------------------
# Public factory
# ---------------------------------------------------------------------------


def bind_memory(
    spec: str | MemoryBackend,
    scope: Scope,
    *,
    max_recall: int = 5,
    write_policy: Callable[[str], bool] | None = None,
) -> "MemoryBinding":
    """Create a :class:`MemoryBinding` from a backend name or an existing backend.

    Args:
        spec: A backend name (``"inprocess"``, ``"mem0"``, ``"graphiti"``) — resolved
            via :func:`coactra.memory.factory.make_backend` — or an already-constructed
            :class:`~coactra.memory.backends.base.MemoryBackend` instance.
        scope: A :class:`~coactra.memory.types.Scope` object that namespaces every
            remember/recall call.  Tenant isolation is enforced by the backend; this
            connector threads the scope through without modification.  (Accepting raw
            kwargs and building a Scope on-the-fly is a known future convenience; the
            current implementation requires a pre-built Scope instance.)
        max_recall: Maximum number of recollections injected into the context string
            returned by :meth:`MemoryBinding.recall`.  Defaults to ``5``.
        write_policy: Optional ``Callable[[str], bool]``.  Called with the raw text
            before each ``remember``; returns ``True`` to allow, ``False`` to veto.
            ``None`` means always allow.

    Returns:
        A configured :class:`MemoryBinding`.
    """
    if isinstance(spec, str):
        backend: MemoryBackend = _make_backend(spec)
    else:
        backend = spec
    return MemoryBinding(backend=backend, scope=scope, max_recall=max_recall, write_policy=write_policy)


# ---------------------------------------------------------------------------
# MemoryBinding
# ---------------------------------------------------------------------------


class MemoryBinding:
    """Stateless (except config) connector that auto-recalls and auto-remembers.

    Never instantiate directly — use :func:`bind_memory`.
    """

    def __init__(
        self,
        *,
        backend: MemoryBackend,
        scope: Scope,
        max_recall: int,
        write_policy: Callable[[str], bool] | None,
    ) -> None:
        self._backend = backend
        self._scope = scope
        self._max_recall = max_recall
        self._write_policy = write_policy

    # ------------------------------------------------------------------
    # Public async API
    # ------------------------------------------------------------------

    async def recall(self, query: str) -> str:
        """Return the top-``max_recall`` recollections as a context string.

        Delegates to ``backend.recall(query, scope, k=max_recall)``.  Formats the
        resulting :class:`~coactra.memory.types.Recollection` objects as one fact per
        line (plain text).  Returns ``""`` if the backend returns nothing relevant.
        """
        hits = await self._backend.recall(query, self._scope, k=self._max_recall)
        # Defensive slice: honour the cap even if the backend ignores k.
        hits = hits[: self._max_recall]
        if not hits:
            return ""
        return "\n".join(r.text for r in hits)

    async def remember(self, text: str, *, source: str | None = None) -> None:  # noqa: ARG002
        """Store *text* in the backend if the write policy permits.

        Args:
            text: The plain-text fact or conversational fragment to store.
            source: Optional provenance tag (e.g. ``"turn-42"``).  Accepted for
                API stability and future use; the current ``MemoryBackend`` Protocol
                has no metadata channel on ``remember``, so ``source`` is not forwarded
                to the backend today.  When a backend exposes a provenance seam this
                connector can attach it without a breaking API change.

        The backend's own extraction/consolidation logic applies; coactra does not
        re-implement ranking or deduplication here.
        """
        if self._write_policy is not None and not self._write_policy(text):
            return  # vetoed — no-op
        # Protocol: remember(events: Sequence[MemoryEvent], scope: Scope) -> None
        await self._backend.remember([text], self._scope)
