"""Workspace — the agent desk facade.

Thin control layer over a WorkspaceBackend + a Scope. It adds the charter's value-add ON
TOP of raw persistence: scoped write/read, run() that enforces CliPolicy BEFORE delegating
to backend.exec, a handoff/day-note, rule-based auto-compact, and storage for a passive
CapabilityManifest. It does NOT mount MCP capabilities (agent runtime's job) and does NOT
own hierarchy/policy (organization's job). Persistent by default.

DESIGN OVERRIDE (locked): commands are arg-lists run with shell=False. run() accepts a
convenience string (split via shlex) or an argv list; either way the policy gate and the
backend operate on the argv list, never a shell string.
"""

from __future__ import annotations

import json
import shutil
import tempfile
from collections.abc import Mapping, Sequence
from datetime import date
from pathlib import Path
from typing import Any

from coactra.scope import Scope, is_safe_path_component
from coactra.workspace.backends.base import WorkspaceBackend
from coactra.workspace.models import CapabilityManifest, ExecOptions, ExecResult
from coactra.workspace.policy import CliPolicy

_MANIFEST_FILE = ".workspace/manifest.json"
_HANDOFF_FILE = "HANDOFF.md"


class Workspace:
    """The agent's persistent desk."""

    def __init__(
        self,
        *,
        backend: WorkspaceBackend,
        scope: Scope,
        policy: CliPolicy | None = None,
        ephemeral: bool = False,
    ) -> None:
        self._backend = backend
        self._scope = scope
        self._policy = policy or CliPolicy()
        self._ephemeral = ephemeral

    @property
    def scope(self) -> Scope:
        return self._scope

    @property
    def root(self) -> str:
        """Absolute path of this desk's root."""
        return self._backend.root_for(self._scope)

    def ensure_layout(
        self,
        directories: Sequence[str],
        templates: Mapping[str, str] | None = None,
    ) -> None:
        """Create desk directories and missing template files through the backend.

        Existing files are preserved so initialization is idempotent.
        """
        for path in directories:
            self._backend.make_dir(path, self._scope)
        for path, data in (templates or {}).items():
            try:
                self._backend.read_file(path, self._scope)
            except FileNotFoundError:
                self._backend.write_file(path, data, self._scope)

    def write(self, path: str, data: str) -> None:
        self._backend.write_file(path, data, self._scope)

    def read(self, path: str) -> str:
        return self._backend.read_file(path, self._scope)

    def list(self) -> list[str]:
        return self._backend.list_files(self._scope)

    def run(
        self,
        command: str | Sequence[str],
        *,
        options: ExecOptions | None = None,
    ) -> ExecResult:
        # Policy normalizes to argv and raises PolicyError before exec is reached.
        argv = self._policy.check(command)
        return self._backend.exec(argv, self._scope, options)

    def set_manifest(self, manifest: CapabilityManifest) -> None:
        self._backend.write_file(_MANIFEST_FILE, manifest.model_dump_json(), self._scope)

    def manifest(self) -> CapabilityManifest:
        try:
            raw = self._backend.read_file(_MANIFEST_FILE, self._scope)
        except (FileNotFoundError, ValueError):
            return CapabilityManifest()
        return CapabilityManifest(**json.loads(raw))

    def _read_handoff_entries(self) -> list[str]:
        try:
            raw = self._backend.read_file(_HANDOFF_FILE, self._scope)
        except (FileNotFoundError, ValueError):
            return []
        return [line for line in raw.splitlines() if line.strip()]

    def handoff(self, note: str) -> None:
        """Append a day-note line so the next session picks up where this one left off."""
        entries = self._read_handoff_entries()
        entries.append(f"- {note}")
        self._backend.write_file(_HANDOFF_FILE, "\n".join(entries) + "\n", self._scope)

    def day_note(self) -> str:
        """The current handoff/day-note text."""
        try:
            return self._backend.read_file(_HANDOFF_FILE, self._scope)
        except (FileNotFoundError, ValueError):
            return ""

    def rotate_journal(
        self,
        *,
        before: date,
        journal_dir: str = "journal",
        archive_dir: str = "archive/journal",
    ) -> list[str]:
        """Move dated journal files older than ``before`` into an archive directory.

        Journal entries are files directly below ``journal_dir`` named
        ``YYYY-MM-DD.*``. The operation uses only backend primitives, so it works for
        local desks and remote sandbox providers alike. Returns archived paths.
        """
        prefix = journal_dir.rstrip("/") + "/"
        archive = archive_dir.rstrip("/")
        moved: list[str] = []
        for path in self.list():
            if not path.startswith(prefix):
                continue
            relative = path[len(prefix) :]
            if "/" in relative:
                continue
            try:
                entry_date = date.fromisoformat(relative[:10])
            except ValueError:
                continue
            if entry_date >= before:
                continue
            destination = f"{archive}/{relative}"
            self.write(destination, self.read(path))
            self._backend.delete_file(path, self._scope)
            moved.append(destination)
        return sorted(moved)

    def compact(self, *, max_entries: int = 50) -> int:
        """Auto-compact: keep only the newest max_entries handoff lines. Rule-based, no LLM.

        Returns the number of entries dropped. Compaction is deterministic (a count cap),
        not summarization — workspace has no model and depends only on pydantic.
        """
        entries = self._read_handoff_entries()
        if len(entries) <= max_entries:
            return 0
        kept = entries[-max_entries:]
        dropped = len(entries) - len(kept)
        self._backend.write_file(_HANDOFF_FILE, "\n".join(kept) + "\n", self._scope)
        return dropped

    def close(self) -> None:
        """Release the desk. Ephemeral desks are deleted; persistent ones are left intact."""
        if self._ephemeral:
            shutil.rmtree(self.root, ignore_errors=True)

    def __enter__(self) -> Workspace:
        return self

    def __exit__(self, *exc: Any) -> None:
        self.close()


def open_workspace(
    *,
    scope: Scope,
    base_dir: str | Path | None = None,
    policy: CliPolicy | None = None,
    ephemeral: bool = False,
    allow_unsafe_local_exec: bool = False,
) -> Workspace:
    """Open the default (LocalFilesystem) desk for scope.

    Persistent by default: files live under base_dir/<tenant>/<namespace>/<agent> across sessions.
    ephemeral=True uses a throwaway temp dir cleaned up on close(). Local subprocesses are
    not jailed; pass allow_unsafe_local_exec=True only for trusted local development.
    Local command execution requires an explicit policy.
    """
    from coactra.workspace.backends.local import LocalFilesystemBackend

    _validate_workspace_scope(scope)
    if ephemeral:
        base = tempfile.mkdtemp(prefix="fleet-ws-ephemeral-")
    else:
        base = base_dir or ".fleet-workspaces"
    if allow_unsafe_local_exec and policy is None:
        raise ValueError("allow_unsafe_local_exec=True requires an explicit CliPolicy")
    backend = LocalFilesystemBackend(
        base_dir=base,
        allow_unsafe_exec=allow_unsafe_local_exec,
    )
    return Workspace(backend=backend, scope=scope, policy=policy, ephemeral=ephemeral)


def _validate_workspace_scope(scope: Scope) -> None:
    """Enforce filesystem-safe tenant, namespace, and agent path components."""
    if scope.agent_id is None:
        raise ValueError("agent_id is required to create a workspace scope")
    for field, value in (
        ("tenant_id", scope.tenant_id),
        ("namespace", scope.namespace),
        ("agent_id", scope.agent_id),
    ):
        if not is_safe_path_component(value):
            raise ValueError(f"{field} must be a safe workspace path component")
