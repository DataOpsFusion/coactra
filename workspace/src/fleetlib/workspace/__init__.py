"""fleetlib.workspace — the persistent agent desk.

A thin control layer ABOVE persistent sandbox backends (local filesystem by default;
Daytona / E2B / OpenHands optional). The backend persists files + runs commands; this
layer adds the "desk": scoped files, a CLI policy gate, a handoff/day-note, rule-based
auto-compact, and storage for a capability-manifest REFERENCE. It does NOT mount MCP
capabilities (the agent runtime does) and does NOT own hierarchy/policy (organization does).
"""

from fleetlib.workspace.backend import WorkspaceBackend
from fleetlib.workspace.desk import Workspace, open_workspace
from fleetlib.workspace.local import LocalFilesystemBackend
from fleetlib.workspace.models import CapabilityManifest, ExecResult
from fleetlib.workspace.policy import CliPolicy, PolicyError
from fleetlib.workspace.scope import Scope

__all__ = [
    "__version__",
    "Scope",
    "ExecResult",
    "CapabilityManifest",
    "CliPolicy",
    "PolicyError",
    "WorkspaceBackend",
    "LocalFilesystemBackend",
    "Workspace",
    "open_workspace",
]

__version__ = "0.1.0"
