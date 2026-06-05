"""Tenant-routed workspace backends for hard physical silo isolation."""
from __future__ import annotations

from coactra._routing import TenantRouter
from coactra.workspace.backends.base import WorkspaceBackend
from coactra.workspace.models import ExecOptions, ExecResult
from coactra.workspace.scope import Scope


class TenantWorkspaceBackendRouter(TenantRouter[WorkspaceBackend]):
    """Delegate each scoped operation to one cached backend per tenant.

    Caching/dispatch comes from :class:`coactra._routing.TenantRouter`; this subclass
    adds only the ``WorkspaceBackend`` contract delegators.
    """

    def root_for(self, scope: Scope) -> str:
        return self.for_tenant(scope.tenant_id).root_for(scope)

    def make_dir(self, path: str, scope: Scope) -> None:
        self.for_tenant(scope.tenant_id).make_dir(path, scope)

    def write_file(self, path: str, data: str, scope: Scope) -> None:
        self.for_tenant(scope.tenant_id).write_file(path, data, scope)

    def read_file(self, path: str, scope: Scope) -> str:
        return self.for_tenant(scope.tenant_id).read_file(path, scope)

    def list_files(self, scope: Scope) -> list[str]:
        return self.for_tenant(scope.tenant_id).list_files(scope)

    def delete_file(self, path: str, scope: Scope) -> None:
        self.for_tenant(scope.tenant_id).delete_file(path, scope)

    def exec(
        self,
        command: list[str],
        scope: Scope,
        options: ExecOptions | None = None,
    ) -> ExecResult:
        return self.for_tenant(scope.tenant_id).exec(command, scope, options)
