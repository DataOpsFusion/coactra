import coactra.workspace as w


def test_public_surface_is_complete():
    expected = {
        "__version__",
        "Scope",
        "ExecResult",
        "CapabilityManifest",
        "CliPolicy",
        "PolicyError",
        "WorkspaceBackend",
        "LocalFilesystemBackend",
        "UnsafeLocalExecError",
        "Workspace",
        "open_workspace",
    }
    assert expected <= set(w.__all__)
    for name in expected:
        assert hasattr(w, name), name


def test_end_to_end_open_write_run_handoff(tmp_path):
    scope = w.Scope(tenant_id="acme", agent_id="planner")
    ws = w.open_workspace(
        scope=scope,
        base_dir=tmp_path,
        policy=w.CliPolicy(deny=["rm"]),
        allow_unsafe_local_exec=True,
    )

    ws.write("plan.md", "step 1: provision")
    assert ws.read("plan.md") == "step 1: provision"

    res = ws.run("echo working")
    assert res.ok and "working" in res.stdout

    ws.set_manifest(w.CapabilityManifest(refs=["mcp://gateway/call_tool"]))
    ws.handoff("next: run step 2")

    # A fresh session over the same scope resumes the desk.
    ws2 = w.open_workspace(scope=scope, base_dir=tmp_path)
    assert ws2.read("plan.md") == "step 1: provision"
    assert ws2.manifest().refs == ["mcp://gateway/call_tool"]
    assert "run step 2" in ws2.day_note()
