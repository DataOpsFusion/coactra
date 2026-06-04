"""Optional bridges to established workflow, protocol, and telemetry libraries."""

from coactra.orchestration.work.adapters._optional import MissingExtraError
from coactra.orchestration.work.adapters.a2a import to_a2a_agent_card, to_a2a_artifact, to_a2a_skill
from coactra.orchestration.work.adapters.cloudevents import to_cloudevent
from coactra.orchestration.work.adapters.dapr import DaprDispatcher
from coactra.orchestration.work.adapters.dbos import DBOSDispatcher
from coactra.orchestration.work.adapters.fsspec import FsspecArtifactStore
from coactra.orchestration.work.adapters.mcp_tasks import (
    MCPTask,
    MCPTaskNotTerminalError,
    MCPTaskPage,
    MCPTasksAdapter,
    to_mcp_task,
)
from coactra.orchestration.work.adapters.opentelemetry import OpenTelemetryAuditSink
from coactra.orchestration.work.adapters.temporal import TemporalDispatcher

__all__ = [
    "DaprDispatcher",
    "DBOSDispatcher",
    "FsspecArtifactStore",
    "MissingExtraError",
    "MCPTask",
    "MCPTaskNotTerminalError",
    "MCPTaskPage",
    "MCPTasksAdapter",
    "to_mcp_task",
    "OpenTelemetryAuditSink",
    "TemporalDispatcher",
    "to_a2a_agent_card",
    "to_a2a_artifact",
    "to_a2a_skill",
    "to_cloudevent",
]
