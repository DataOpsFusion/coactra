from fleetlib.ai.protocols import EmbeddingFn, ReasoningStore, Completer


def test_protocols_are_runtime_checkable():
    class FakeEmbed:
        def __call__(self, text: str) -> list[float]:
            return [0.0]

    assert isinstance(FakeEmbed(), EmbeddingFn)


def test_completer_protocol_shape():
    class FakeCompleter:
        def complete(self, model: str, messages: list[dict], **kw) -> str:
            return "ok"

    assert isinstance(FakeCompleter(), Completer)


def test_reasoning_store_protocol_shape():
    class FakeStore:
        def put(self, tenant, trace): ...
        def search(self, tenant, vector, k, min_quality): return []
        def get(self, tenant, trace_id): return None

    assert isinstance(FakeStore(), ReasoningStore)
