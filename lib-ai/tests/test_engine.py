from fleetlib.ai.engine import ReasoningEngine
from fleetlib.ai.models import Decision
from fleetlib.ai.store import InMemoryStore


class FixedEmbed:
    """Maps known problems to fixed vectors so similarity is deterministic."""

    def __init__(self, table):
        self.table = table

    def __call__(self, text):
        return self.table.get(text, [0.0, 0.0])


def make_engine(table, reasoner):
    return ReasoningEngine(
        store=InMemoryStore(),
        embed=FixedEmbed(table),
        reasoner=reasoner,
        k=3,
        min_quality=0.4,
    )


def test_capture_then_replay_on_similar_problem():
    table = {"P1": [1.0, 0.0], "P1b": [1.0, 0.01]}
    calls = []
    eng = make_engine(table, lambda p: calls.append(p) or "FRESH")

    tid = eng.capture("tenant", "P1", "REASON-1")
    # mark it proven so the adaptive gate lowers the bar
    for _ in range(20):
        eng.record_outcome("tenant", tid, True)

    res = eng.recall_or_reason("tenant", "P1b")
    assert res.decision == Decision.REPLAY
    assert res.answer == "REASON-1"
    assert res.reasoned_fresh is False
    assert calls == []  # reasoner NOT called


def test_branch_b_candidate_but_gate_rejects_re_reasons():
    table = {"P1": [1.0, 0.0], "FAR": [0.2, 1.0]}
    eng = make_engine(table, lambda p: "FRESH")
    tid = eng.capture("tenant", "P1", "REASON-1")
    for _ in range(20):
        eng.record_outcome("tenant", tid, True)

    # FAR is too dissimilar -> even a proven trace can't clear the bar.
    res = eng.recall_or_reason("tenant", "FAR")
    assert res.decision == Decision.RE_REASON
    assert res.answer == "FRESH"
    assert res.reasoned_fresh is True


def test_branch_c_no_quality_candidate_re_reasons():
    table = {"P1": [1.0, 0.0], "P1b": [1.0, 0.01]}
    eng = make_engine(table, lambda p: "FRESH")
    tid = eng.capture("tenant", "P1", "REASON-1")
    # poison quality below min_quality -> filtered out before the gate
    for _ in range(20):
        eng.record_outcome("tenant", tid, False)

    res = eng.recall_or_reason("tenant", "P1b")
    assert res.decision == Decision.RE_REASON
    assert res.answer == "FRESH"


def test_re_reason_auto_captures_for_next_time():
    table = {"P1": [1.0, 0.0]}
    eng = make_engine(table, lambda p: "FRESH-REASONING")
    res = eng.recall_or_reason("tenant", "P1")  # cold: nothing stored
    assert res.decision == Decision.RE_REASON
    # the fresh reasoning is now captured and replayable
    assert eng.store.get("tenant", res.trace_id) is not None


def test_tenant_isolation_in_recall():
    table = {"P1": [1.0, 0.0]}
    eng = make_engine(table, lambda p: "FRESH")
    tid = eng.capture("tenant-a", "P1", "REASON-A")
    for _ in range(20):
        eng.record_outcome("tenant-a", tid, True)
    # tenant-b asks the same problem -> miss -> re-reason
    res = eng.recall_or_reason("tenant-b", "P1")
    assert res.decision == Decision.RE_REASON
