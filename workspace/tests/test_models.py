from fleetlib.workspace import CapabilityManifest, ExecResult


def test_exec_result_fields():
    r = ExecResult(exit_code=0, stdout="hi\n", stderr="")
    assert r.exit_code == 0
    assert r.ok is True
    assert r.stdout == "hi\n"


def test_exec_result_nonzero_is_not_ok():
    assert ExecResult(exit_code=1, stdout="", stderr="boom").ok is False


def test_manifest_is_passive_data_only():
    # The agent runtime mounts MCP capabilities; workspace only STORES the reference.
    m = CapabilityManifest(refs=["mcp://gateway/search_tools", "mcp://gateway/call_tool"])
    assert m.refs[0] == "mcp://gateway/search_tools"
    # Boundary lock: no mount/connect/activate behavior lives on the manifest.
    assert not hasattr(m, "mount")
    assert not hasattr(m, "connect")
    assert not hasattr(m, "activate")


def test_manifest_defaults_empty():
    assert CapabilityManifest().refs == []
