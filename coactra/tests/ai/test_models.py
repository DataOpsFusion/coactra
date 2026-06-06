from coactra.ai.models import ReasoningTrace, Decision


def test_trace_starts_neutral_quality():
    t = ReasoningTrace(id="t1", problem="p", reasoning="r", embedding=[0.1])
    # no outcomes yet -> neutral prior (0.5), not 0 and not 1
    assert t.quality == 0.5
    assert t.successes == 0 and t.failures == 0


def test_quality_tracks_outcomes():
    t = ReasoningTrace(id="t1", problem="p", reasoning="r", embedding=[0.1])
    t.record(True)
    t.record(True)
    t.record(False)
    # Laplace-smoothed success rate: (2+1)/(3+2) = 0.6
    assert abs(t.quality - 0.6) < 1e-9
    assert t.successes == 2 and t.failures == 1


def test_decision_enum_values():
    assert {d.value for d in Decision} == {"replay", "re_reason"}
