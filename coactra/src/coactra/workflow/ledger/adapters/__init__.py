"""Optional bridges to established workflow, protocol, and telemetry libraries."""

from coactra.workflow.ledger.adapters._optional import MissingExtraError
from coactra.workflow.ledger.adapters.a2a import to_a2a_agent_card, to_a2a_artifact, to_a2a_skill
from coactra.workflow.ledger.adapters.cloudevents import to_cloudevent
from coactra.workflow.ledger.adapters.dapr import DaprDispatcher
from coactra.workflow.ledger.adapters.dbos import DBOSDispatcher
from coactra.workflow.ledger.adapters.fsspec import FsspecArtifactStore
from coactra.workflow.ledger.adapters.mcp_tasks import (
    MCPTask,
    MCPTaskNotTerminalError,
    MCPTaskPage,
    MCPTasksAdapter,
    to_mcp_task,
)
from coactra.workflow.ledger.adapters.opentelemetry import OpenTelemetryAuditSink
from coactra.workflow.ledger.adapters.temporal import TemporalDispatcher

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
