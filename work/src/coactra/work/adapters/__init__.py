"""Optional bridges to established workflow, protocol, and telemetry libraries."""

from coactra.work.adapters._optional import MissingExtraError
from coactra.work.adapters.a2a import to_a2a_agent_card, to_a2a_artifact, to_a2a_skill
from coactra.work.adapters.cloudevents import to_cloudevent
from coactra.work.adapters.dapr import DaprDispatcher
from coactra.work.adapters.dbos import DBOSDispatcher
from coactra.work.adapters.fsspec import FsspecArtifactStore
from coactra.work.adapters.opentelemetry import OpenTelemetryAuditSink
from coactra.work.adapters.temporal import TemporalDispatcher

__all__ = [
    "DaprDispatcher",
    "DBOSDispatcher",
    "FsspecArtifactStore",
    "MissingExtraError",
    "OpenTelemetryAuditSink",
    "TemporalDispatcher",
    "to_a2a_agent_card",
    "to_a2a_artifact",
    "to_a2a_skill",
    "to_cloudevent",
]
