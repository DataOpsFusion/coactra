from fleetlib.workspace import Scope, open_workspace

SCOPE = Scope(tenant_id="acme", agent_id="planner")


def test_files_persist_across_instances(tmp_path):
    ws1 = open_workspace(scope=SCOPE, base_dir=tmp_path)
    ws1.write("notes.md", "kept between sessions")
    ws1.handoff("resume the migration")

    # A brand-new Workspace over the same scope/dir is a "next session".
    ws2 = open_workspace(scope=SCOPE, base_dir=tmp_path)
    assert ws2.read("notes.md") == "kept between sessions"
    assert "resume the migration" in ws2.day_note()


def test_ephemeral_mode_does_not_persist():
    ws = open_workspace(scope=SCOPE, ephemeral=True)
    ws.write("scratch.txt", "temporary")
    root = ws.root
    ws.close()

    import os

    assert not os.path.exists(root)  # ephemeral desk is cleaned up on close


def test_open_workspace_defaults_to_persistent(tmp_path):
    ws = open_workspace(scope=SCOPE, base_dir=tmp_path)
    ws.write("a.txt", "1")
    ws.close()
    import os

    assert os.path.exists(ws.root)  # persistent desk survives close
