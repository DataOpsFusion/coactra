from datetime import datetime, timezone

from fleetlib.memory import MemoryEvent, MemoryItem, Provenance


def test_event_minimal():
    e = MemoryEvent(content="user prefers dark mode")
    assert e.content == "user prefers dark mode"
    assert e.kind == "lesson"


def test_item_from_event_carries_provenance():
    e = MemoryEvent(content="deploy succeeded on attempt 2", kind="summary")
    item = MemoryItem.from_event(e, source_backend="inprocess")
    assert item.content == "deploy succeeded on attempt 2"
    assert item.kind == "summary"
    assert isinstance(item.id, str) and item.id
    assert isinstance(item.provenance, Provenance)
    assert item.provenance.source_backend == "inprocess"
    assert isinstance(item.provenance.created_at, datetime)
    assert item.provenance.created_at.tzinfo is timezone.utc


def test_item_provenance_is_never_optional():
    # MemoryItem MUST be constructed with provenance — there is no silent default.
    assert "provenance" in MemoryItem.model_fields
    assert MemoryItem.model_fields["provenance"].is_required()
