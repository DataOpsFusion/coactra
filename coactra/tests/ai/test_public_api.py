import coactra.ai as ai


def test_public_exports_present():
    for name in [
        "ask",
        "structured",
        "ReasoningEngine",
        "ReasoningTrace",
        "Decision",
        "InMemoryStore",
        "AdaptiveGate",
        "LiteLLMEmbedding",
    ]:
        assert hasattr(ai, name), name


def test_engine_constructible_from_public_api():
    eng = ai.ReasoningEngine(
        store=ai.InMemoryStore(),
        embed=lambda t: [1.0, 0.0],
        reasoner=lambda p: "R",
    )
    tid = eng.capture("t", "prob", "reason")
    assert eng.store.get("t", tid).reasoning == "reason"
