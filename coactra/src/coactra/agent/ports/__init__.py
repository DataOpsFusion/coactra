"""ports/ — the six narrow capability Protocols + their in-process fakes.

The agent consumes ai/memory/workspace/orchestration(workflow + work)/organization ONLY through these
Protocols; it never imports `coactra.<sibling>`. Each port mirrors the real sibling
facade so live wiring is a thin adapter. Each ships a faithful in-process fake default.
"""

from coactra.agent.ports.fakes import (
    FakeAI,
    FakeMember,
    FakeMemory,
    FakeOrganization,
    FakeOrgNode,
    FakeWorkflow,
    FakeWorkspace,
    FakeWork,
)
from coactra.agent.ports.protocols import (
    AIPort,
    MemoryPort,
    OrganizationPort,
    WorkflowPort,
    WorkspacePort,
    WorkPort,
)

__all__ = [
    "AIPort",
    "MemoryPort",
    "WorkspacePort",
    "WorkflowPort",
    "OrganizationPort",
    "WorkPort",
    "FakeAI",
    "FakeMemory",
    "FakeWorkspace",
    "FakeWorkflow",
    "FakeOrganization",
    "FakeWork",
    "FakeOrgNode",
    "FakeMember",
]
