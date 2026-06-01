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
from collections.abc import Sequence
from pathlib import Path

from coactra.workspace.backend import WorkspaceBackend
from coactra.workspace.models import CapabilityManifest, ExecResult
from coactra.workspace.policy import CliPolicy
from coactra.workspace.scope import Scope

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

    def write(self, path: str, data: str) -> None:
        self._backend.write_file(path, data, self._scope)

    def read(self, path: str) -> str:
        return self._backend.read_file(path, self._scope)

    def list(self) -> list[str]:
        return self._backend.list_files(self._scope)

    def run(self, command: str | Sequence[str]) -> ExecResult:
        # Policy normalizes to argv and raises PolicyError before exec is reached.
        argv = self._policy.check(command)
        return self._backend.exec(argv, self._scope)

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


def open_workspace(
    *,
    scope: Scope,
    base_dir: str | Path | None = None,
    policy: CliPolicy | None = None,
    ephemeral: bool = False,
) -> Workspace:
    """Open the default (LocalFilesystem) desk for scope.

    Persistent by default: files live under base_dir/<tenant>/<agent> across sessions.
    ephemeral=True uses a throwaway temp dir cleaned up on close().
    """
    from coactra.workspace.local import LocalFilesystemBackend

    if ephemeral:
        base = tempfile.mkdtemp(prefix="fleet-ws-ephemeral-")
    else:
        base = base_dir or ".fleet-workspaces"
    backend = LocalFilesystemBackend(base_dir=base)
    return Workspace(backend=backend, scope=scope, policy=policy, ephemeral=ephemeral)
