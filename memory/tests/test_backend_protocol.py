from fleetlib.memory import Capability, MemoryBackend, MemoryEvent, MemoryItem, Scope


class _Dummy:
    def capabilities(self) -> set[Capability]:
        return {Capability.STORE}

    def learn(self, events, scope: Scope) -> list[MemoryItem]:
        return []

    def recall(self, query, scope, capabilities=None, limit=10):
        return []

    def dump(self, scope: Scope) -> list[MemoryItem]:
        return []

    def ingest(self, items, scope: Scope) -> list[MemoryItem]:
        return []


def test_protocol_is_runtime_checkable():
    assert isinstance(_Dummy(), MemoryBackend)


def test_incomplete_class_is_not_a_backend():
    class Partial:
        def learn(self, events, scope):
            return []

    assert not isinstance(Partial(), MemoryBackend)


def test_event_normalization_helper_accepts_str_and_event():
    from fleetlib.memory.backend import normalize_events

    out = normalize_events(["a plain string", MemoryEvent(content="already an event")])
    assert all(isinstance(e, MemoryEvent) for e in out)
    assert out[0].content == "a plain string"
