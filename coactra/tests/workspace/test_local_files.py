import pytest

from coactra.workspace import LocalFilesystemBackend, Scope

SCOPE = Scope(tenant_id="acme", agent_id="planner")


def test_write_read_roundtrip(tmp_path):
    be = LocalFilesystemBackend(base_dir=tmp_path)
    be.write_file("notes.md", "hello desk", SCOPE)
    assert be.read_file("notes.md", SCOPE) == "hello desk"


def test_write_creates_nested_dirs(tmp_path):
    be = LocalFilesystemBackend(base_dir=tmp_path)
    be.write_file("sub/dir/file.txt", "x", SCOPE)
    assert be.read_file("sub/dir/file.txt", SCOPE) == "x"


def test_make_dir_creates_empty_nested_dir(tmp_path):
    be = LocalFilesystemBackend(base_dir=tmp_path)
    be.make_dir("journal/daily", SCOPE)
    assert (tmp_path / "acme" / "default" / "planner" / "journal" / "daily").is_dir()


def test_list_and_delete(tmp_path):
    be = LocalFilesystemBackend(base_dir=tmp_path)
    be.write_file("a.txt", "1", SCOPE)
    be.write_file("b/c.txt", "2", SCOPE)
    assert set(be.list_files(SCOPE)) == {"a.txt", "b/c.txt"}
    be.delete_file("a.txt", SCOPE)
    assert set(be.list_files(SCOPE)) == {"b/c.txt"}


def test_root_is_under_tenant_namespace_agent(tmp_path):
    be = LocalFilesystemBackend(base_dir=tmp_path)
    root = be.root_for(SCOPE)
    assert root.endswith("acme/default/planner")


def test_path_traversal_is_confined(tmp_path):
    be = LocalFilesystemBackend(base_dir=tmp_path)
    with pytest.raises(ValueError, match="escapes desk root"):
        be.write_file("../../etc/passwd", "owned", SCOPE)
    with pytest.raises(ValueError, match="escapes desk root"):
        be.read_file("../secret", SCOPE)
