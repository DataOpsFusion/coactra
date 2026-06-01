from fleetlib.memory import Capability, MemoryBackend, Recollection, Scope
from fleetlib.memory.backends.base import event_text, normalize_events


class _Dummy:
    async def remember(self, events, scope: Scope) -> None:
        return None

    async def recall(self, query, scope, k=10) -> list[Recollection]:
        return []

    async def capabilities(self) -> set[Capability]:
        return {Capability.STORE}

    async def dump(self, scope: Scope) -> list[Recollection]:
        return []

    async def ingest(self, items, scope: Scope):
        return None


def test_protocol_is_runtime_checkable():
    assert isinstance(_Dummy(), MemoryBackend)


def test_incomplete_class_is_not_a_backend():
    class Partial:
        async def remember(self, events, scope):
            return None

    assert not isinstance(Partial(), MemoryBackend)


def test_event_text_flattens_str_and_chat_dict():
    assert event_text("plain string") == "plain string"
    assert event_text({"role": "user", "content": "hello"}) == "hello"


def test_normalize_events_returns_concrete_list():
    out = normalize_events(iter(["a", {"role": "user", "content": "b"}]))
    assert isinstance(out, list)
    assert len(out) == 2
