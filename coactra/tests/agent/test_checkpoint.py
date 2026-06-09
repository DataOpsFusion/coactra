"""TDD tests for the checkpoint module — CheckpointStore protocol, InMemoryCheckpointStore,
and WorkflowRun (de)serialization.

RED phase: all tests written before implementation exists.

Covers:
1. InMemoryCheckpointStore — save/load round-trip; load("missing") returns None
2. WorkflowRun round-trip — run_to_state / run_from_state reconstructs equal run
   (ledger, status, pending_index, name, approvals preserved; _steps excluded)
3. JSON-serializable — run_to_state output survives json.dumps
4. Simulate restart — save, fresh context, load + reconstruct preserves completed steps
   and pending_index
"""

from __future__ import annotations

import json

import pytest

from coactra.agent.checkpoint import (
    InMemoryCheckpointStore,
    LangGraphCheckpointStore,
    run_from_state,
    run_to_state,
)
from coactra.workflow.playbook import Approval, StepResult, WorkflowRun

# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


def _make_partial_run() -> WorkflowRun:
    """WorkflowRun interrupted at step 2, with one completed step and one approval."""
    return WorkflowRun(
        name="test-playbook",
        status="interrupted",
        results=[
            StepResult(
                instruction="do the first thing",
                agent="alpha",
                output="result-one",
                status="done",
            ),
        ],
        pending_index=1,
        approvals=[
            Approval(step_index=0, instruction="do the first thing", decision=True),
        ],
        # _steps intentionally left as default [] — it's playbook state, not run state
    )


def _make_completed_run() -> WorkflowRun:
    """WorkflowRun with two completed steps, no pending_index."""
    return WorkflowRun(
        name="two-step-playbook",
        status="completed",
        results=[
            StepResult(
                instruction="step one",
                agent="agent-a",
                output="output-a",
                status="done",
            ),
            StepResult(
                instruction="step two",
                agent="agent-b",
                output="output-b",
                status="done",
            ),
        ],
        pending_index=None,
        approvals=[],
    )


# ---------------------------------------------------------------------------
# 1. InMemoryCheckpointStore
# ---------------------------------------------------------------------------


class TestInMemoryCheckpointStore:
    def test_save_and_load_returns_stored_state(self):
        store = InMemoryCheckpointStore()
        state = {"run_id": "r1", "status": "interrupted", "step": 2}
        store.save("r1", state)
        assert store.load("r1") == state

    def test_load_missing_returns_none(self):
        store = InMemoryCheckpointStore()
        assert store.load("does-not-exist") is None

    def test_save_overwrites_previous(self):
        store = InMemoryCheckpointStore()
        store.save("r1", {"status": "interrupted"})
        store.save("r1", {"status": "completed"})
        assert store.load("r1") == {"status": "completed"}

    def test_multiple_run_ids_are_independent(self):
        store = InMemoryCheckpointStore()
        store.save("r1", {"status": "interrupted"})
        store.save("r2", {"status": "completed"})
        assert store.load("r1") == {"status": "interrupted"}
        assert store.load("r2") == {"status": "completed"}


# ---------------------------------------------------------------------------
# 2. round-trip — run_to_state / run_from_state
# ---------------------------------------------------------------------------


class TestRoundTrip:
    def test_partial_run_round_trips(self):
        original = _make_partial_run()
        reconstructed = run_from_state(run_to_state(original))
        assert reconstructed == original

    def test_completed_run_round_trips(self):
        original = _make_completed_run()
        reconstructed = run_from_state(run_to_state(original))
        assert reconstructed == original

    def test_pending_index_none_preserved(self):
        run = _make_completed_run()
        state = run_to_state(run)
        assert state["pending_index"] is None
        reconstructed = run_from_state(state)
        assert reconstructed.pending_index is None

    def test_pending_index_int_preserved(self):
        run = _make_partial_run()
        state = run_to_state(run)
        assert state["pending_index"] == 1
        reconstructed = run_from_state(state)
        assert reconstructed.pending_index == 1

    def test_results_ledger_preserved(self):
        run = _make_partial_run()
        reconstructed = run_from_state(run_to_state(run))
        assert len(reconstructed.results) == 1
        r = reconstructed.results[0]
        assert r.instruction == "do the first thing"
        assert r.agent == "alpha"
        assert r.output == "result-one"
        assert r.status == "done"

    def test_approvals_preserved(self):
        run = _make_partial_run()
        reconstructed = run_from_state(run_to_state(run))
        assert len(reconstructed.approvals) == 1
        a = reconstructed.approvals[0]
        assert a.step_index == 0
        assert a.instruction == "do the first thing"
        assert a.decision is True

    def test_status_preserved(self):
        run = _make_partial_run()
        reconstructed = run_from_state(run_to_state(run))
        assert reconstructed.status == "interrupted"

    def test_name_preserved(self):
        run = _make_partial_run()
        reconstructed = run_from_state(run_to_state(run))
        assert reconstructed.name == "test-playbook"

    def test_steps_not_in_state(self):
        """_steps is playbook state, not run state — must NOT be serialized."""
        run = _make_partial_run()
        state = run_to_state(run)
        assert "steps" not in state
        assert "_steps" not in state


# ---------------------------------------------------------------------------
# 3. JSON-serializable
# ---------------------------------------------------------------------------


class TestJsonSerializable:
    def test_partial_run_state_is_json_serializable(self):
        run = _make_partial_run()
        state = run_to_state(run)
        # Must not raise
        serialized = json.dumps(state)
        # Deserialize back and verify round-trip through JSON
        reloaded = json.loads(serialized)
        reconstructed = run_from_state(reloaded)
        assert reconstructed == run

    def test_completed_run_state_is_json_serializable(self):
        run = _make_completed_run()
        state = run_to_state(run)
        serialized = json.dumps(state)
        reloaded = json.loads(serialized)
        reconstructed = run_from_state(reloaded)
        assert reconstructed == run


# ---------------------------------------------------------------------------
# 4. Simulate restart — save, fresh store, load, reconstruct
# ---------------------------------------------------------------------------


class TestSimulateRestart:
    def test_restart_preserves_completed_steps_and_pending_index(self):
        run = _make_partial_run()

        # --- Process 1: save to the store ---
        store_p1 = InMemoryCheckpointStore()
        state = run_to_state(run)
        store_p1.save("my-run", state)

        # --- Process 2: fresh store, simulate loading from persistent storage ---
        # (In real usage this would be Redis/DB; we simulate by passing the state dict.)
        stored_state = store_p1.load("my-run")

        store_p2 = InMemoryCheckpointStore()
        store_p2.save("my-run", stored_state)

        loaded_state = store_p2.load("my-run")
        assert loaded_state is not None

        reconstructed = run_from_state(loaded_state)

        # Completed steps are preserved
        assert len(reconstructed.results) == 1
        assert reconstructed.results[0].status == "done"
        assert reconstructed.results[0].output == "result-one"

        # Pending index is preserved so a resume can continue
        assert reconstructed.pending_index == 1

        # Status
        assert reconstructed.status == "interrupted"

    def test_restart_with_no_completed_steps(self):
        """A run interrupted at step 0 (no steps completed yet) also round-trips."""
        run = WorkflowRun(
            name="fresh-run",
            status="interrupted",
            results=[],
            pending_index=0,
            approvals=[],
        )
        store = InMemoryCheckpointStore()
        store.save("fresh", run_to_state(run))
        reconstructed = run_from_state(store.load("fresh"))
        assert reconstructed.results == []
        assert reconstructed.pending_index == 0
        assert reconstructed.status == "interrupted"


# ---------------------------------------------------------------------------
# 5. Durable LangGraph store — persists across store/process recreation
# ---------------------------------------------------------------------------


class _FakeAgent:
    def __init__(self, name: str) -> None:
        self._name = name

    async def run(self, instruction: str) -> str:
        return f"{self._name}: {instruction}"


class _PinnedTeam:
    def __init__(self) -> None:
        self._members = {
            "alpha": _FakeAgent("alpha"),
            "beta": _FakeAgent("beta"),
        }

    def member(self, name: str):
        return self._members.get(name)

    def match_skill(self, skill_id: str):
        return None


@pytest.mark.asyncio
async def test_langgraph_checkpoint_store_resumes_workflow_across_restart(tmp_path):
    pytest.importorskip("langgraph.checkpoint.sqlite")
    from coactra.agent.workflow import Workflow, step

    db = tmp_path / "checkpoints.sqlite"
    run_id = "restartable-run"
    team = _PinnedTeam()
    wf = Workflow(
        "restartable",
        steps=[
            step("collect evidence", agent="alpha"),
            step("apply change", agent="beta", approve=True),
        ],
    )

    first_store = LangGraphCheckpointStore(db)
    interrupted = await wf.run(team, checkpoint=first_store, run_id=run_id)

    assert interrupted.status == "interrupted"
    assert interrupted.pending_index == 1

    restarted_store = LangGraphCheckpointStore(db)
    final = await wf.resume_from(restarted_store, run_id, team, decision=True)

    assert final.status == "completed"
    assert [r.agent for r in final.results] == ["alpha", "beta"]
    assert [r.status for r in final.results] == ["done", "done"]
