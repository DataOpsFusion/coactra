import pytest

from fleetlib.memory import MemoryBackend, make_backend
from fleetlib.memory.backends._errors import MissingExtraError
from fleetlib.memory.backends.inprocess import InProcessBackend


def test_make_inprocess_returns_backend():
    be = make_backend("inprocess")
    assert isinstance(be, InProcessBackend)
    assert isinstance(be, MemoryBackend)


def test_unknown_name_raises_value_error():
    with pytest.raises(ValueError, match="unknown backend"):
        make_backend("redis")


def test_mem0_without_extra_raises_missing_extra():
    # mem0ai is NOT installed in the offline test env → ctor raises MissingExtraError.
    with pytest.raises(MissingExtraError) as exc:
        make_backend("mem0")
    assert exc.value.extra == "mem0"


def test_graphiti_without_extra_raises_missing_extra():
    with pytest.raises(MissingExtraError) as exc:
        make_backend("graphiti")
    assert exc.value.extra == "graphiti"


def test_engine_backed_backend_accepts_injected_client():
    # With a client injected, no extra is needed — factory forwards **config.
    sentinel = object()
    be = make_backend("mem0", client=sentinel)
    assert isinstance(be, MemoryBackend)
