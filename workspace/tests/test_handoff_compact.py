from coactra.workspace import LocalFilesystemBackend, Scope, Workspace

SCOPE = Scope(tenant_id="acme", agent_id="planner")


def _ws(tmp_path):
    return Workspace(backend=LocalFilesystemBackend(base_dir=tmp_path), scope=SCOPE)


def test_handoff_appends_entries(tmp_path):
    ws = _ws(tmp_path)
    ws.handoff("tomorrow: finish the deploy")
    ws.handoff("also: rotate the cert")
    note = ws.day_note()
    assert "finish the deploy" in note
    assert "rotate the cert" in note


def test_handoff_persists_to_a_file(tmp_path):
    ws = _ws(tmp_path)
    ws.handoff("pick up here")
    assert "HANDOFF.md" in ws.list()


def test_compact_caps_entries_by_rule_keeping_newest(tmp_path):
    ws = _ws(tmp_path)
    for i in range(10):
        ws.handoff(f"entry {i}")
    dropped = ws.compact(max_entries=3)
    note = ws.day_note()
    assert dropped == 7
    assert "entry 9" in note
    assert "entry 0" not in note
    assert note.count("entry ") == 3


def test_compact_noop_when_under_limit(tmp_path):
    ws = _ws(tmp_path)
    ws.handoff("only one")
    assert ws.compact(max_entries=5) == 0
    assert "only one" in ws.day_note()
