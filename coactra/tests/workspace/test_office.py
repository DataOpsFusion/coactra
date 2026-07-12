from __future__ import annotations

from datetime import date
from pathlib import Path

import pytest

from coactra.workspace.office import (
    OFFICE_SUBDIRS,
    OfficeWorkspace,
    StatusValidationError,
    count_office_tokens,
    validate_status,
)


def test_valid_status_parses():
    pytest.importorskip("yaml")
    status = validate_status(
        """---
current_assignment_id: WO-118
current_step: 2
last_action_timestamp: 2026-05-28T10:00:00+00:00
blockers: []
next_action: provision VM
---
"""
    )
    assert status.current_assignment_id == "WO-118"
    assert status.current_step == 2


def test_invalid_status_missing_field_raises():
    pytest.importorskip("yaml")
    with pytest.raises(StatusValidationError, match="last_action_timestamp"):
        validate_status("---\ncurrent_assignment_id: WO-118\n---\n")


def test_count_tokens_returns_int(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    class WordEncoder:
        def encode(self, text: str) -> list[str]:
            return text.split()

    monkeypatch.setattr(
        "coactra.workspace.office._get_encoder",
        lambda _: WordEncoder(),
    )
    (tmp_path / "STATUS.md").write_text("hello world " * 100)
    count = count_office_tokens(tmp_path)
    assert count == 200


def test_initialize_scaffolds_office_and_preserves_existing_files(tmp_path: Path):
    office = OfficeWorkspace.open(
        office_dir=tmp_path / "platform",
        tenant_id="default",
        agent_id="platform",
    )
    office.initialize()
    assert office.root == tmp_path / "default" / "platform"
    assert all((office.root / subdir).is_dir() for subdir in OFFICE_SUBDIRS)
    assert "platform" in office.read("STATUS.md")

    office.write("STATUS.md", "keep me")
    office.initialize()
    assert office.read("STATUS.md") == "keep me"


def test_rotate_journal_archives_old_dated_files(tmp_path: Path):
    office = OfficeWorkspace.open(
        office_dir=tmp_path / "platform",
        tenant_id="default",
        agent_id="platform",
    )
    office.initialize()
    office.write("journal/2026-01-02.md", "old")
    office.write("journal/2026-06-02.md", "current")

    moved = office.rotate_journal(before=date(2026, 2, 1))

    assert moved == ["journal/daily/2026-01-02.md"]
    assert office.read("journal/daily/2026-01-02.md") == "old"
