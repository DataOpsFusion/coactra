from coactra.workspace import LocalFilesystemBackend, Scope

ACME_A = Scope(tenant_id="acme", agent_id="planner")
ACME_B = Scope(tenant_id="acme", agent_id="builder")
GLOBEX_A = Scope(tenant_id="globex", agent_id="planner")


def test_agents_in_same_tenant_are_isolated(tmp_path):
    be = LocalFilesystemBackend(base_dir=tmp_path)
    be.write_file("note.md", "planner only", ACME_A)
    assert be.list_files(ACME_B) == []


def test_tenants_are_isolated(tmp_path):
    be = LocalFilesystemBackend(base_dir=tmp_path)
    be.write_file("note.md", "acme planner", ACME_A)
    be.write_file("note.md", "globex planner", GLOBEX_A)
    assert be.read_file("note.md", ACME_A) == "acme planner"
    assert be.read_file("note.md", GLOBEX_A) == "globex planner"
