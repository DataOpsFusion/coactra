"""coactra.workspace — the persistent agent desk.

A thin control layer ABOVE persistent sandbox backends (local filesystem by default;
provider integrations such as Daytona / E2B / OpenHands satisfy the same
``WorkspaceBackend`` seam when implemented). The backend persists files and may run
commands; this layer adds the "desk": scoped files, a CLI
policy gate, a handoff/day-note, rule-based auto-compact, and storage for a
capability-manifest REFERENCE. It does NOT mount MCP capabilities (the agent runtime does)
and does NOT own hierarchy/policy (organization does).
"""

from coactra._version import distribution_version

from coactra.workspace.backends.base import WorkspaceBackend
from coactra.workspace.backends.local import (
    LocalFilesystemBackend,
    UnsafeLocalExecError,
)
from coactra.workspace.desk import Workspace, open_workspace
from coactra.workspace.errors import WorkspaceError
from coactra.workspace.models import CapabilityManifest, ExecOptions, ExecResult
from coactra.workspace.policy import CliPolicy, PolicyError
from coactra.workspace.routing import TenantWorkspaceBackendRouter
from coactra.workspace.scope import Scope

__all__ = [
    "__version__",
    "Scope",
    "WorkspaceError",
    "ExecResult",
    "ExecOptions",
    "CapabilityManifest",
    "CliPolicy",
    "PolicyError",
    "WorkspaceBackend",
    "LocalFilesystemBackend",
    "UnsafeLocalExecError",
    "TenantWorkspaceBackendRouter",
    "Workspace",
    "open_workspace",
]

__version__ = distribution_version()
