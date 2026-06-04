from coactra.workspace import (
    ExecOptions,
    ExecResult,
    LocalFilesystemBackend,
    Scope,
    TenantWorkspaceBackendRouter,
    Workspace,
    WorkspaceBackend,
)


def test_tenant_workspace_router_binds_a_distinct_physical_backend_per_tenant(tmp_path):
    built = []

    def factory(tenant_id):
        built.append(tenant_id)
        return LocalFilesystemBackend(tmp_path / tenant_id)

    router = TenantWorkspaceBackendRouter(factory)
    assert isinstance(router, WorkspaceBackend)
    acme = Workspace(backend=router, scope=Scope(tenant_id="acme", agent_id="builder"))
    globex = Workspace(backend=router, scope=Scope(tenant_id="globex", agent_id="builder"))
    acme.write("note.txt", "acme")
    globex.write("note.txt", "globex")

    assert acme.read("note.txt") == "acme"
    assert globex.read("note.txt") == "globex"
    assert built == ["acme", "globex"]


def test_tenant_workspace_router_forwards_exec_options():
    class RecordingBackend:
        def __init__(self):
            self.calls = []

        def root_for(self, scope):
            return f"/tmp/{scope.tenant_id}/{scope.agent_id}"

        def make_dir(self, path, scope):
            pass

        def write_file(self, path, data, scope):
            pass

        def read_file(self, path, scope):
            return ""

        def list_files(self, scope):
            return []

        def delete_file(self, path, scope):
            pass

        def exec(self, command, scope, options=None):
            self.calls.append((command, scope, options))
            return ExecResult(exit_code=0, stdout="ok")

    backend = RecordingBackend()
    router = TenantWorkspaceBackendRouter(lambda tenant: backend)
    scope = Scope(tenant_id="acme", agent_id="builder")
    options = ExecOptions(timeout_seconds=3, cwd="work")

    result = router.exec(["pwd"], scope, options)

    assert result.ok
    assert backend.calls == [(["pwd"], scope, options)]

