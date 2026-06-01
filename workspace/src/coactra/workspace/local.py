"""LocalFilesystemBackend — the ONE working default backend.

A persistent directory per desk: <base_dir>/<tenant_id>/<agent_id>/. Files survive across
process restarts (persistent by default). Every relative path is resolved and checked to
stay inside the desk root — traversal (e.g. "../../etc/passwd") is rejected. This is the
opinionated default that works out of the box; advanced users swap in Daytona/E2B/OpenHands.

DESIGN OVERRIDE (locked): exec() takes argv (list[str]) and runs subprocess with
shell=False — no shell string, no shell=True anywhere.
"""

from __future__ import annotations

import subprocess
from pathlib import Path

from coactra.workspace.models import ExecResult
from coactra.workspace.scope import Scope


class LocalFilesystemBackend:
    """Tenant/agent-isolated filesystem desk with traversal confinement."""

    def __init__(self, base_dir: str | Path = ".fleet-workspaces") -> None:
        self._base = Path(base_dir)

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
