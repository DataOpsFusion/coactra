"""Checkpoint — durability seam for WorkflowRun.

Provides a swappable store abstraction so a Workflow run can survive a process
restart and resume from the last completed step.  The default implementation
is in-memory; LangGraph, Temporal, Redis, or any key-value backend can be
substituted by satisfying the :class:`CheckpointStore` protocol.

Public API
----------
- ``CheckpointStore``       — structural Protocol (save / load).
- ``InMemoryCheckpointStore`` — dict-backed default implementation.
- ``run_to_state``          — serialize a :class:`WorkflowRun` to a plain,
                              JSON-serializable dict.
- ``run_from_state``        — reconstruct a :class:`WorkflowRun` from such a dict.

Integration note
----------------
The actual ``Workflow.run(checkpoint=…)`` / resume wiring lives in an
integration pass that imports these helpers.  This module has no dependency on
``Workflow`` itself — only on the run-ledger dataclasses.
"""
from __future__ import annotations

from typing import Protocol, runtime_checkable

from coactra.agent.workflow import Approval, StepResult, WorkflowRun


# ---------------------------------------------------------------------------
# Protocol
# ---------------------------------------------------------------------------

@runtime_checkable
class CheckpointStore(Protocol):
    """Minimal contract for a checkpoint backend."""

    def save(self, run_id: str, state: dict) -> None:
        """Persist *state* under *run_id*, overwriting any previous value."""
        ...

    def load(self, run_id: str) -> dict | None:
        """Return the state stored under *run_id*, or ``None`` if absent."""
        ...


# ---------------------------------------------------------------------------
# In-memory implementation
# ---------------------------------------------------------------------------

class InMemoryCheckpointStore:
    """Simple dict-backed :class:`CheckpointStore`.

    Suitable for testing, single-process use, and as the out-of-the-box
    default.  Not thread-safe; replace with a Redis/DB-backed store for
    production durability.
    """

    def __init__(self) -> None:
        self._store: dict[str, dict] = {}

    def save(self, run_id: str, state: dict) -> None:
        """Store *state* under *run_id*, replacing any previous entry."""
        self._store[run_id] = state

    def load(self, run_id: str) -> dict | None:
        """Return the stored state for *run_id*, or ``None`` if not found."""
        return self._store.get(run_id)


# ---------------------------------------------------------------------------
# (De)serialization helpers
# ---------------------------------------------------------------------------

def run_to_state(run: WorkflowRun) -> dict:
    """Serialize *run* to a plain, JSON-serializable dict.

    Only run-state fields are included (``name``, ``status``, ``results``,
    ``pending_index``, ``approvals``).  The ``_steps`` field is **excluded**
    because it is playbook *definition* state, not run state — the Workflow
    object reattaches it on resume via its own Playbook reference.

    Parameters
    ----------
    run:
        The :class:`WorkflowRun` to serialize.

    Returns
    -------
    dict
        A plain dict suitable for ``json.dumps`` or storage in any key-value
        backend.
    """
    return {
        "name": run.name,
        "status": run.status,
        "pending_index": run.pending_index,
        "results": [
            {
                "instruction": r.instruction,
                "agent": r.agent,
                "output": r.output,
                "status": r.status,
            }
            for r in run.results
        ],
        "approvals": [
            {
                "step_index": a.step_index,
                "instruction": a.instruction,
                "decision": a.decision,
            }
            for a in run.approvals
        ],
    }


def run_from_state(state: dict) -> WorkflowRun:
    """Reconstruct a :class:`WorkflowRun` from a serialized state dict.

    The ``_steps`` field is left as its default (``[]``) — the integration
    layer is responsible for reattaching the playbook steps when resuming.

    Parameters
    ----------
    state:
        A dict previously produced by :func:`run_to_state` (or loaded from
        JSON / a key-value store).

    Returns
    -------
    :class:`WorkflowRun`
    """
    results = [
        StepResult(
            instruction=r["instruction"],
            agent=r["agent"],
            output=r["output"],
            status=r["status"],
        )
        for r in state.get("results", [])
    ]
    approvals = [
        Approval(
            step_index=a["step_index"],
            instruction=a["instruction"],
            decision=bool(a["decision"]),
        )
        for a in state.get("approvals", [])
    ]
    return WorkflowRun(
        name=state["name"],
        status=state["status"],
        results=results,
        pending_index=state.get("pending_index"),
        approvals=approvals,
        # _steps intentionally omitted — defaults to [] per dataclass field_factory
    )
