import pytest

from fleetlib.ai.adapters.chroma import ChromaStore


def test_chroma_store_requires_extra():
    # chromadb not installed in the dev env -> constructing must raise clearly.
    with pytest.raises(ImportError, match="chromadb"):
        ChromaStore(collection="reasoning")


def test_chroma_store_is_a_reasoning_store_type():
    from fleetlib.ai.protocols import ReasoningStore

    # The class declares the Protocol methods even though it needs the extra.
    for method in ("put", "search", "get"):
        assert hasattr(ChromaStore, method)
    assert hasattr(ReasoningStore, "__subclasshook__")
