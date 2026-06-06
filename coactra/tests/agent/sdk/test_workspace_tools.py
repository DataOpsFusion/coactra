"""Tests for workspace_tools — the bridge between a Workspace and agent tool callables.

TDD: tests were written first; implementation is in
coactra/src/coactra/agent/sdk/workspace_tools.py.
"""

from __future__ import annotations

import pytest

from coactra.workspace import Scope, open_workspace
from coactra.workspace.policy import PolicyError
from coactra.agent.sdk.workspace_tools import workspace_tools


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture()
def ws():
    """Ephemeral workspace with local exec enabled (for run tests)."""
    scope = Scope(tenant_id="test-tenant", agent_id="test-agent")
    workspace = open_workspace(
        scope=scope,
        ephemeral=True,
        allow_unsafe_local_exec=True,
    )
    yield workspace
    workspace.close()


@pytest.fixture()
def tools(ws):
    """Default tools (allow_run=False)."""
    return workspace_tools(ws)


@pytest.fixture()
def tools_with_run(ws):
    """Tools with run enabled; only 'echo' is allowed."""
    return workspace_tools(ws, allow_run=True, allow=("echo",))


# ---------------------------------------------------------------------------
# Helper
# ---------------------------------------------------------------------------


def _tool_names(tools_list):
    return {fn.__name__ for fn in tools_list}


# ---------------------------------------------------------------------------
# 1. Default tools — run NOT present
# ---------------------------------------------------------------------------


def test_default_tools_contains_read_write_list(tools):
    names = _tool_names(tools)
    assert "read_file" in names
    assert "write_file" in names
    assert "list_files" in names


def test_default_tools_does_not_contain_run(tools):
    names = _tool_names(tools)
    assert "run" not in names


# ---------------------------------------------------------------------------
# 2. Write / read roundtrip + list
# ---------------------------------------------------------------------------


def test_write_then_read_roundtrip(tools):
    write_file = next(fn for fn in tools if fn.__name__ == "write_file")
    read_file = next(fn for fn in tools if fn.__name__ == "read_file")

    confirmation = write_file("hello.txt", "hello world")
    assert isinstance(confirmation, str)
    assert confirmation  # non-empty confirmation string

    content = read_file("hello.txt")
    assert content == "hello world"


def test_list_files_shows_written_file(tools):
    write_file = next(fn for fn in tools if fn.__name__ == "write_file")
    list_files = next(fn for fn in tools if fn.__name__ == "list_files")

    write_file("notes.txt", "some content")
    files = list_files()

    assert isinstance(files, list)
    assert any("notes.txt" in f for f in files)


# ---------------------------------------------------------------------------
# 3. run — present only when allow_run=True
# ---------------------------------------------------------------------------


def test_run_present_when_allow_run_true(tools_with_run):
    names = _tool_names(tools_with_run)
    assert "run" in names


def test_run_echo_works(tools_with_run):
    run = next(fn for fn in tools_with_run if fn.__name__ == "run")
    result = run("echo hi")
    assert "hi" in result


def test_run_blocks_non_allowlisted_command(tools_with_run):
    """Commands not in the allow list must be refused at the tool layer."""
    run = next(fn for fn in tools_with_run if fn.__name__ == "run")
    with pytest.raises((PolicyError, PermissionError, ValueError, RuntimeError)):
        run("rm -rf /")


def test_run_blocks_empty_allow_is_default_deny(ws):
    """allow_run=True with empty allow tuple must refuse all commands."""
    tools_no_allow = workspace_tools(ws, allow_run=True, allow=())
    run = next(fn for fn in tools_no_allow if fn.__name__ == "run")
    with pytest.raises((PolicyError, PermissionError, ValueError, RuntimeError)):
        run("echo hi")
