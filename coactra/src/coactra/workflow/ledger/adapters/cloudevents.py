"""CloudEvents SDK conversion for work audit envelopes."""

from __future__ import annotations

from typing import Any

from coactra.workflow.ledger.adapters._optional import optional_module
from coactra.workflow.ledger.domain.events import EventEnvelope


def to_cloudevent(event: EventEnvelope) -> Any:
    """Convert a work event into ``cloudevents.http.CloudEvent``."""
    http = optional_module("cloudevents.http", extra="cloudevents")
    attributes = {
        "specversion": event.specversion,
        "id": event.id,
        "source": event.source,
        "type": event.type,
        "time": event.time.isoformat(),
    }
    if event.subject is not None:
        attributes["subject"] = event.subject
    return http.CloudEvent(attributes, event.data)
