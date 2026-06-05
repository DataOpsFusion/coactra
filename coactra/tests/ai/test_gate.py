from coactra.ai.gate import AdaptiveGate
from coactra.ai.models import ReasoningTrace


def _trace(succ, fail):
    return ReasoningTrace(id="t", problem="p", reasoning="r", embedding=[1.0], successes=succ, failures=fail)


def test_boundary_moves_with_outcomes():
    gate = AdaptiveGate(base_threshold=0.90)
    sim = 0.85  # below the static base bar

    # Untrusted trace (no verified successes): borderline sim is REJECTED.
    cold = _trace(succ=0, fail=0)
    assert gate.accept(similarity=sim, trace=cold) is False

    # Same similarity, same trace once it has many verified-correct replays:
    # the required bar drops below 0.85 -> now ACCEPTED. Boundary moved.
    proven = _trace(succ=20, fail=0)
    assert gate.accept(similarity=sim, trace=proven) is True


def test_failures_raise_the_bar():
    gate = AdaptiveGate(base_threshold=0.90)
    # A trace that has failed a lot must clear a HIGHER bar than a fresh one.
    bad = _trace(succ=0, fail=20)
    good = _trace(succ=20, fail=0)
    assert gate.required(bad) > gate.required(good)


def test_required_never_below_floor():
    gate = AdaptiveGate(base_threshold=0.90, floor=0.70)
    perfect = _trace(succ=1000, fail=0)
    assert gate.required(perfect) >= 0.70


def test_confidence_combines_similarity_and_quality():
    gate = AdaptiveGate(base_threshold=0.90)
    proven = _trace(succ=20, fail=0)
    c = gate.confidence(similarity=0.85, trace=proven)
    assert 0.0 <= c <= 1.0
    # higher quality -> higher confidence at equal similarity
    weak = _trace(succ=0, fail=0)
    assert gate.confidence(0.85, proven) > gate.confidence(0.85, weak)
