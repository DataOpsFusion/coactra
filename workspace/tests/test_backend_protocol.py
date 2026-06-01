from coactra.workspace import ExecResult, Scope, WorkspaceBackend

SCOPE = Scope(tenant_id="acme", agent_id="planner")


class _Dummy:
    def root_for(self, scope: Scope) -> str:
        return "/tmp/x"

    def write_file(self, path: str, data: str, scope: Scope) -> None:
        return None

    def read_file(self, path: str, scope: Scope) -> str:
        return ""

    def list_files(self, scope: Scope) -> list[str]:
        return []

    def delete_file(self, path: str, scope: Scope) -> None:
        return None

    def exec(self, command: list[str], scope: Scope) -> ExecResult:
        return ExecResult(exit_code=0)


def test_protocol_is_runtime_checkable():
    assert isinstance(_Dummy(), WorkspaceBackend)


def test_incomplete_class_is_not_a_backend():
    class Partial:
        def read_file(self, path, scope):
            return ""

    assert not isinstance(Partial(), WorkspaceBackend)
