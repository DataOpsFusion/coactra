"""Optional office profile built on the persistent workspace desk."""

from __future__ import annotations

import functools
import re
from dataclasses import dataclass
from datetime import UTC, date, datetime, timedelta
from pathlib import Path
from typing import Any

from pydantic import BaseModel, Field, ValidationError

from coactra.workspace.desk import Workspace, open_workspace
from coactra.workspace.policy import CliPolicy
from coactra.workspace.scope import Scope

TOKEN_BUDGET = 8000

STATUS_MD_TEMPLATE = """---
current_assignment_id: null
current_step: null
last_action_timestamp: {ts}
blockers: []
next_action: null
---

# {agent_id} - Status

I am {agent_id}. Nothing assigned right now.
"""

INDEX_MD_TEMPLATE = """# {agent_id} - Office Index

- `STATUS.md` - current state, machine-readable
- `inbox/` - incoming messages
- `assignments/` - assigned work
- `journal/` - chronological activity log
- `brain/` - durable notes
- `drafts/` - work-in-progress text
"""

OFFICE_SUBDIRS = (
    "inbox",
    "assignments",
    "journal",
    "journal/daily",
    "journal/weekly",
    "brain",
    "drafts",
)


@dataclass(frozen=True)
class OfficeLayout:
    """Configurable files and directories materialized for an office desk."""

    directories: tuple[str, ...] = OFFICE_SUBDIRS
    status_template: str = STATUS_MD_TEMPLATE
    index_template: str = INDEX_MD_TEMPLATE


class StatusValidationError(ValueError):
    """Raised when ``STATUS.md`` frontmatter does not match the schema."""


class StatusSchema(BaseModel):
    current_assignment_id: str | None
    last_action_timestamp: datetime
    current_step: int | None
    blockers: list[str] = Field(default_factory=list)
    next_action: str | None = None


_FRONTMATTER_RE = re.compile(r"^---\n(.*?)\n---", re.DOTALL)


def validate_status(text: str) -> StatusSchema:
    """Parse and validate YAML frontmatter from an office ``STATUS.md`` file."""
    match = _FRONTMATTER_RE.match(text)
    if not match:
        raise StatusValidationError("STATUS.md is missing YAML frontmatter")
    import yaml

    try:
        data = yaml.safe_load(match.group(1))
    except yaml.YAMLError as exc:
        raise StatusValidationError(f"STATUS.md frontmatter is not valid YAML: {exc}") from exc
    try:
        return StatusSchema.model_validate(data)
    except ValidationError as exc:
        first = exc.errors()[0]
        loc = ".".join(str(part) for part in first["loc"])
        raise StatusValidationError(f"STATUS.md invalid: {loc}: {first['msg']}") from exc


@functools.lru_cache(maxsize=4)
def _get_encoder(name: str) -> Any:
    import tiktoken

    return tiktoken.get_encoding(name)


def count_office_tokens(
    office_root: Path,
    *,
    encoding: str = "cl100k_base",
    recent_days: int = 7,
) -> int:
    """Count tokens in core office files, durable notes, and recent journal entries."""
    encoder = _get_encoder(encoding)
    files: list[Path] = []
    for name in ("STATUS.md", "INDEX.md"):
        path = office_root / name
        if path.exists():
            files.append(path)
    brain = office_root / "brain"
    if brain.exists():
        files.extend(brain.glob("*.md"))
    journal = office_root / "journal"
    if journal.exists():
        cutoff = datetime.now(UTC) - timedelta(days=recent_days)
        for path in journal.glob("*.md"):
            try:
                if datetime.fromtimestamp(path.stat().st_mtime, tz=UTC) > cutoff:
                    files.append(path)
            except OSError:
                continue
    total = 0
    for path in files:
        try:
            total += len(encoder.encode(path.read_text(encoding="utf-8")))
        except (UnicodeDecodeError, OSError):
            continue
    return total


class OfficeWorkspace:
    """Persistent per-agent office backed by a scoped :class:`Workspace`."""

    def __init__(
        self,
        workspace: Workspace,
        agent_id: str,
        *,
        layout: OfficeLayout | None = None,
    ) -> None:
        self._ws = workspace
        self.agent_id = agent_id
        self._layout = layout or OfficeLayout()

    @classmethod
    def open(
        cls,
        *,
        office_dir: Path | str,
        tenant_id: str,
        agent_id: str,
        policy: CliPolicy | None = None,
        layout: OfficeLayout | None = None,
        allow_unsafe_local_exec: bool = False,
    ) -> OfficeWorkspace:
        """Open an office rooted at ``office_dir.parent/tenant_id/agent_id``.

        The explicit tenant and agent segments keep the local backend aligned with
        the same scope contract used by remote sandbox backends. Callers should use
        :attr:`root` as the canonical office path after opening the desk.
        """
        base_dir = Path(office_dir).parent
        scope = Scope(tenant_id=tenant_id, agent_id=agent_id)
        workspace = open_workspace(
            scope=scope,
            base_dir=base_dir,
            policy=policy,
            allow_unsafe_local_exec=allow_unsafe_local_exec,
        )
        return cls(workspace, agent_id, layout=layout)

    @property
    def root(self) -> Path:
        return Path(self._ws.root)

    @property
    def journal_dir(self) -> Path:
        return self.root / "journal"

    def initialize(self) -> None:
        """Materialize missing office directories and templates idempotently."""
        self._ws.ensure_layout(
            self._layout.directories,
            {
                "STATUS.md": self._layout.status_template.format(
                    ts=datetime.now(UTC).isoformat(),
                    agent_id=self.agent_id,
                ),
                "INDEX.md": self._layout.index_template.format(agent_id=self.agent_id),
            },
        )

    def write(self, path: str, data: str) -> None:
        self._ws.write(path, data)

    def read(self, path: str) -> str:
        return self._ws.read(path)

    def list(self) -> list[str]:
        return self._ws.list()

    def handoff(self, note: str) -> None:
        self._ws.handoff(note)

    def day_note(self) -> str:
        return self._ws.day_note()

    def compact_handoff(self, *, max_entries: int = 50) -> int:
        return self._ws.compact(max_entries=max_entries)

    def rotate_journal(self, *, before: date) -> list[str]:
        return self._ws.rotate_journal(before=before, archive_dir="journal/daily")

    def run(self, command: str | list[str]):
        return self._ws.run(command)
