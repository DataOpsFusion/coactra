"""LocalFilesystemBackend — the ONE working default backend.

A persistent directory per desk: <base_dir>/<tenant_id>/<agent_id>/. Files survive across
process restarts (persistent by default). Every relative file path is resolved and checked to stay inside the desk root — traversal
(e.g. "../../etc/passwd") is rejected. Local subprocesses are not filesystem jails, so
exec is disabled unless trusted development explicitly opts in. Production execution for
mutually untrusted tenants belongs in a sandbox-backed adapter.

DESIGN OVERRIDE (locked): exec() takes argv (list[str]) and runs subprocess with
shell=False — no shell string, no shell=True anywhere.
"""

from __future__ import annotations

import subprocess
from pathlib import Path

from coactra.workspace.models import ExecResult
from coactra.workspace.scope import Scope


class LocalFilesystemBackend:
    """Tenant/agent-isolated filesystem desk with traversal-confined file operations.

    Local subprocesses are not filesystem jails. Enable them only for trusted local
    development; use a sandbox-backed adapter for mutually untrusted tenants.
    """

    def __init__(
        self,
        base_dir: str | Path = ".fleet-workspaces",
        *,
        allow_unsafe_exec: bool = False,
    ) -> None:
        self._base = Path(base_dir)
        self._allow_unsafe_exec = allow_unsafe_exec

    def _root_path(self, scope: Scope) -> Path:
        root = (self._base / scope.tenant_id / scope.agent_id).resolve()
        root.mkdir(parents=True, exist_ok=True)
        return root

    def _resolve(self, path: str, scope: Scope) -> Path:
        root = self._root_path(scope)
        target = (root / path).resolve()
        if root != target and root not in target.parents:
            raise ValueError(f"path {path!r} escapes desk root")
        return target

    def root_for(self, scope: Scope) -> str:
        return str(self._root_path(scope))

    def write_file(self, path: str, data: str, scope: Scope) -> None:
        target = self._resolve(path, scope)
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(data, encoding="utf-8")

    def read_file(self, path: str, scope: Scope) -> str:
        return self._resolve(path, scope).read_text(encoding="utf-8")

    def list_files(self, scope: Scope) -> list[str]:
        root = self._root_path(scope)
        return sorted(
            str(p.relative_to(root)) for p in root.rglob("*") if p.is_file()
        )

    def delete_file(self, path: str, scope: Scope) -> None:
        self._resolve(path, scope).unlink(missing_ok=True)

    def exec(self, command: list[str], scope: Scope) -> ExecResult:
        if not self._allow_unsafe_exec:
            raise UnsafeLocalExecError(
                "local subprocess execution is not filesystem-jailed; "
                "pass allow_unsafe_exec=True only for trusted local development"
            )
        root = self._root_path(scope)
        completed = subprocess.run(
            command,
            shell=False,
            cwd=str(root),
            capture_output=True,
            text=True,
        )
        return ExecResult(
            exit_code=completed.returncode,
            stdout=completed.stdout,
            stderr=completed.stderr,
        )


class UnsafeLocalExecError(PermissionError):
    """Raised when unjailed local subprocess execution was not explicitly enabled."""
