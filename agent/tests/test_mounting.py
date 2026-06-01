import pytest

from fleetlib.agent import (
    MCPServerPort,
    MountConflictError,
    MountRegistry,
    NamespaceByMountId,
    Scope,
)


class FakeServer:
    """An in-process MCPServerPort: just returns the tool names it was constructed with."""

    def __init__(self, names):
        self._names = list(names)

    def list_tools(self):
        return list(self._names)


ACME = Scope(tenant_id="acme")


def test_server_satisfies_port():
    assert isinstance(FakeServer(["a"]), MCPServerPort)


def test_keystone_mount_is_not_visible_until_next_turn():
    reg = MountRegistry(scope=ACME)
    # Turn 0 toolset is whatever is already active (nothing yet).
    assert reg.active_tools() == []

    # Mid-turn mount: staged into pending, effective on the NEXT safe turn only.
    reg.stage("fs", FakeServer(["read_file"]))
    assert reg.active_tools() == []  # still not visible this turn

    # The turn boundary promotes pending -> active.
    reg.begin_turn()
    names = {t.qualified_name for t in reg.active_tools()}
    assert names == {"fs.read_file"}


def test_begin_turn_fires_invalidate_callback():
    fired = []
    reg = MountRegistry(scope=ACME, on_invalidate=lambda: fired.append(True))
    reg.stage("fs", FakeServer(["read_file"]))
    reg.begin_turn()
    assert fired == [True]


def test_idle_begin_turn_does_not_fire_invalidate():
    fired = []
    reg = MountRegistry(scope=ACME, on_invalidate=lambda: fired.append(True))
    reg.begin_turn()  # nothing pending
    assert fired == []


def test_conflict_default_namespaces_by_mount_id():
    reg = MountRegistry(scope=ACME)
    reg.stage("fs", FakeServer(["read"]))
    reg.stage("db", FakeServer(["read"]))  # same bare name, different mount
    reg.begin_turn()
    names = {t.qualified_name for t in reg.active_tools()}
    assert names == {"fs.read", "db.read"}  # no collision — namespaced


def test_conflict_policy_can_reject():
    class RejectOnConflict:
        def resolve(self, incoming, active):
            if any(a.name == incoming.name for a in active):
                raise MountConflictError(incoming.name)
            return incoming

    reg = MountRegistry(scope=ACME, conflict_policy=RejectOnConflict())
    reg.stage("fs", FakeServer(["read"]))
    reg.begin_turn()
    reg.stage("db", FakeServer(["read"]))
    with pytest.raises(MountConflictError):
        reg.begin_turn()


def test_namespace_by_mount_id_is_the_default_policy():
    reg = MountRegistry(scope=ACME)
    assert isinstance(reg.conflict_policy, NamespaceByMountId)


def test_registry_is_tenant_scoped():
    reg = MountRegistry(scope=Scope(tenant_id="acme", namespace="agent:1"))
    assert reg.scope.tenant_id == "acme"
