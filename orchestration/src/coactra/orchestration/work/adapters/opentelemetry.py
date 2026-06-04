"""OpenTelemetry audit sink.

Libraries should depend only on the OpenTelemetry API; the consuming application chooses
and configures its SDK and exporter.
"""

from __future__ import annotations

from typing import Any

from coactra.orchestration.work.adapters._optional import optional_module
from coactra.orchestration.work.domain.events import EventEnvelope


class OpenTelemetryAuditSink:
    """Emit work transitions as events on a short-lived lifecycle span."""

    def __init__(self, tracer: Any | None = None) -> None:
        if tracer is None:
            trace = optional_module("opentelemetry.trace", extra="otel")
            tracer = trace.get_tracer("coactra.work")
        self.tracer = tracer

    def emit(self, event: EventEnvelope) -> None:
        attributes = {
            "coactra.work.event_id": event.id,
            "coactra.work.tenant_id": event.tenant_id,
        }
        if event.subject is not None:
            attributes["coactra.work.id"] = event.subject
        with self.tracer.start_as_current_span(event.type, attributes=attributes) as span:
            span.add_event(event.type, attributes=_flat_attributes(event.data))


def _flat_attributes(data: dict[str, Any]) -> dict[str, Any]:
    """Keep only attribute values accepted by OpenTelemetry's API."""
    return {
        key: value
        for key, value in data.items()
        if isinstance(value, (bool, str, bytes, int, float))
        or (
            isinstance(value, (list, tuple))
            and all(isinstance(item, (bool, str, bytes, int, float)) for item in value)
        )
    }
