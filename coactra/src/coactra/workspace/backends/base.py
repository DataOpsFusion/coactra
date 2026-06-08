"""WorkspaceBackend — the swappable persistence + exec primitive.

A backend is DUMB on purpose: it persists files and may run commands rooted at one desk,
and nothing more. Filesystem confinement for file operations is mandatory; secure command
execution requires a sandbox-backed adapter. Desk features (CLI policy, handoff,
compact, manifest) live in the
Workspace facade above it, which is what keeps the backend swappable. Every method takes a
Scope; confinement to <root>/<tenant_id>/<agent_id> is part of the contract. The default is
LocalFilesystemBackend; provider integrations (Daytona/E2B/OpenHands, etc.) satisfy this
same seam when implemented.

DESIGN OVERRIDE (locked): exec() takes an arg-list (argv: list[str]) and runs it with
shell=False — never a shell string.
"""

from __future__ import annotations

from typing import Protocol, runtime_checkable

from coactra.workspace.models import ExecOptions, ExecResult
from coactra.workspace.scope import Scope


@runtime_checkable
class WorkspaceBackend(Protocol):
    def root_for(self, scope: Scope) -> str:
        """Absolute path of the desk root for scope (created on demand)."""
        ...

    def make_dir(self, path: str, scope: Scope) -> None:
        """Create path (relative to the desk root) within scope."""
        ...

    def write_file(self, path: str, data: str, scope: Scope) -> None:
        """Write data to path (relative to the desk root) within scope."""
        ...

    def read_file(self, path: str, scope: Scope) -> str:
        """Read path (relative to the desk root) within scope."""
        ...

    def list_files(self, scope: Scope) -> list[str]:
        """List relative file paths under the desk root for scope."""
        ...

    def delete_file(self, path: str, scope: Scope) -> None:
        """Delete path (relative to the desk root) within scope."""
        ...

    def exec(
        self,
        command: list[str],
        scope: Scope,
        options: ExecOptions | None = None,
    ) -> ExecResult:
        """Run argv within the backend sandbox, or reject when confinement is unavailable."""
        ...
