"""ports/ — the five narrow sibling Protocols + their in-process fakes.

The agent consumes ai/memory/workspace/workflow/organization ONLY through these
Protocols; it never imports `fleetlib.<sibling>`. Each port mirrors the real sibling
facade so live wiring is a thin adapter. Each ships a faithful in-process fake default.
"""

from fleetlib.agent.ports.fakes import (
    FakeAI,
    FakeMember,
    FakeMemory,
    FakeOrganization,
    FakeOrgNode,
    FakeWorkflow,
    FakeWorkspace,
)
from fleetlib.agent.ports.protocols import (
    AIPort,
    MemoryPort,
    OrganizationPort,
    WorkflowPort,
    WorkspacePort,
)

__all__ = [
    "AIPort",
    "MemoryPort",
    "WorkspacePort",
    "WorkflowPort",
    "OrganizationPort",
    "FakeAI",
    "FakeMemory",
    "FakeWorkspace",
    "FakeWorkflow",
    "FakeOrganization",
    "FakeOrgNode",
    "FakeMember",
]
