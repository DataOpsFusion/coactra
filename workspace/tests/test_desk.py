import pytest

from coactra.workspace import (
    CapabilityManifest,
    CliPolicy,
    LocalFilesystemBackend,
    PolicyError,
    Scope,
    Workspace,
)

SCOPE = Scope(tenant_id="acme", agent_id="planner")


def _ws(tmp_path, **kw):
    return Workspace(backend=LocalFilesystemBackend(base_dir=tmp_path), scope=SCOPE, **kw)


def test_write_and_read(tmp_path):
    ws = _ws(tmp_path)
    ws.write("notes.md", "first day")
    assert ws.read("notes.md") == "first day"


def test_run_returns_exec_result(tmp_path):
    ws = _ws(tmp_path)
    res = ws.run("echo hi")
    assert res.exit_code == 0
    assert "hi" in res.stdout


def test_run_enforces_policy_before_exec(tmp_path):
    ws = _ws(tmp_path, policy=CliPolicy(deny=["rm"]))
    # If policy let it through, this file would be deleted; assert it is NOT reached.
    ws.write("keep.txt", "safe")
    with pytest.raises(PolicyError, match="rm"):
        ws.run("rm keep.txt")
    assert ws.read("keep.txt") == "safe"


def test_manifest_round_trip_is_stored_not_mounted(tmp_path):
    ws = _ws(tmp_path)
    assert ws.manifest().refs == []
    ws.set_manifest(CapabilityManifest(refs=["mcp://gateway/call_tool"]))
    assert ws.manifest().refs == ["mcp://gateway/call_tool"]
    # Boundary: the facade STORES the manifest; it never mounts capabilities.
    assert not hasattr(ws, "mount")
