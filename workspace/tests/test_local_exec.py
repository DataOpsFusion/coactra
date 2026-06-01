"""DESIGN OVERRIDE (locked): backend.exec takes an arg-list (argv: list[str]) and runs it
with shell=False — never a shell string. Tests pass argv lists accordingly."""

import pytest

from coactra.workspace import (
    ExecResult,
    LocalFilesystemBackend,
    Scope,
    UnsafeLocalExecError,
)

SCOPE = Scope(tenant_id="acme", agent_id="planner")


def test_exec_returns_exec_result(tmp_path):
    be = LocalFilesystemBackend(base_dir=tmp_path, allow_unsafe_exec=True)
    res = be.exec(["echo", "hello"], SCOPE)
    assert isinstance(res, ExecResult)
    assert res.exit_code == 0
    assert "hello" in res.stdout


def test_exec_runs_with_desk_as_cwd(tmp_path):
    be = LocalFilesystemBackend(base_dir=tmp_path, allow_unsafe_exec=True)
    be.write_file("marker.txt", "present", SCOPE)
    res = be.exec(["ls"], SCOPE)
    assert "marker.txt" in res.stdout


def test_exec_captures_nonzero_exit_and_stderr(tmp_path):
    be = LocalFilesystemBackend(base_dir=tmp_path, allow_unsafe_exec=True)
    res = be.exec(["ls", "/no/such/path/xyz"], SCOPE)
    assert res.exit_code != 0
    assert res.ok is False
    assert res.stderr != ""


def test_exec_is_disabled_by_default_because_cwd_is_not_a_filesystem_jail(tmp_path):
    be = LocalFilesystemBackend(base_dir=tmp_path)

    with pytest.raises(UnsafeLocalExecError, match="not filesystem-jailed"):
        be.exec(["cat", "../../globex/planner/secret.txt"], SCOPE)
