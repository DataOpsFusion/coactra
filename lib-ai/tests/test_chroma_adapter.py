import pytest

from coactra.ai.adapters.chroma import ChromaStore


def test_chroma_store_requires_extra():
    # chromadb not installed in the dev env -> constructing must raise clearly.
    with pytest.raises(ImportError, match="chromadb"):
        ChromaStore(collection="reasoning")


def test_chroma_store_is_a_reasoning_store_type():
    from coactra.ai.protocols import ReasoningStore

    # The class declares the Protocol methods even though it needs the extra.
    for method in ("put", "search", "get"):
        assert hasattr(ChromaStore, method)
    assert hasattr(ReasoningStore, "__subclasshook__")


class _Collection:
    def __init__(self):
        self.embedding = [1.0, 0.0]
        self.metadata = None
        self.query_kwargs = None

    def upsert(self, *, ids, embeddings, metadatas):
        self.embedding = embeddings[0]
        self.metadata = metadatas[0]

    def get(self, *, ids, include):
        return {"ids": ids, "metadatas": [self.metadata], "embeddings": [self.embedding]}

    def query(self, **kwargs):
        self.query_kwargs = kwargs
        return {"metadatas": [[self.metadata]], "embeddings": [[self.embedding]]}


def _store_with(collection):
    store = object.__new__(ChromaStore)
    store._col = collection
    return store


def test_chroma_store_serializes_nested_trace_meta_as_scalar_json():
    from coactra.ai.models import ReasoningTrace

    collection = _Collection()
    store = _store_with(collection)
    trace = ReasoningTrace(
        id="trace-1",
        problem="deploy",
        reasoning="check health",
        embedding=[1.0, 0.0],
        meta={"nested": {"owner": "platform"}, "labels": ["prod"]},
    )

    store.put("acme", trace)

    assert all(isinstance(value, (str, int, float, bool)) for value in collection.metadata.values())
    assert store.get("acme", "trace-1") == trace


def test_chroma_search_requests_embeddings_and_restores_trace_meta():
    from coactra.ai.models import ReasoningTrace

    collection = _Collection()
    store = _store_with(collection)
    trace = ReasoningTrace(
        id="trace-1",
        problem="deploy",
        reasoning="check health",
        embedding=[1.0, 0.0],
        successes=2,
        meta={"owner": "platform"},
    )
    store.put("acme", trace)

    hits = store.search("acme", [1.0, 0.0], k=1, min_quality=0.0)

    assert collection.query_kwargs["include"] == ["metadatas", "embeddings"]
    assert hits[0][0] == trace
