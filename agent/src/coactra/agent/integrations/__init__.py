"""Optional adapters for composing the standalone Coactra libraries."""

from coactra.agent.integrations.adapters import (
    AIAdapter,
    MemoryAdapter,
    OrganizationAdapter,
    WorkflowAdapter,
    WorkspaceAdapter,
)
from coactra.agent.integrations.factory import make_coactra_agent

__all__ = [
    "AIAdapter",
    "MemoryAdapter",
    "WorkspaceAdapter",
    "WorkflowAdapter",
    "OrganizationAdapter",
    "make_coactra_agent",
]
