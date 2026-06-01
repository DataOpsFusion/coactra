import pytest

from fleetlib.agent import (
    MCPServerPort,
    MountConflictError,
    MountRegistry,
    NamespaceByMountId,
    RejectOnConflict,
    Scope,
    ToolSpec,
    ToolTrie,
)


class FakeServer:
    """An in-process MCPServerPort: returns the tool names it was constructed with."""

    def __init__(self, names):
        self._names = list(names)

    def list_tools(self):
        return list(self._names)


ACME = Scope(tenant_id="acme")


def test_server_satisfies_port():
    assert isinstance(FakeServer(["a"]), MCPServerPort)


# --- the prefix-trie DSA (lookup / prefix enumeration / conflict at terminal) ---------


def test_trie_lookup_is_exact_by_qualified_name():
    trie = ToolTrie()
    trie.insert(ToolSpec(name="read_file", mount_id="fs"))
    trie.insert(ToolSpec(name="write_file", mount_id="fs"))
    assert trie.lookup("fs.read_file") == ToolSpec(name="read_file", mount_id="fs")
    assert trie.lookup("fs.missing") is None
    assert trie.lookup("nope.read_file") is None
    assert len(trie) == 2


def test_trie_prefix_enumeration_walks_one_subtree():
    trie = ToolTrie()
    trie.insert(ToolSpec(name="read", mount_id="fs"))
    trie.insert(ToolSpec(name="write", mount_id="fs"))
    trie.insert(ToolSpec(name="query", mount_id="db"))
    under_fs = {t.qualified_name for t in trie.under("fs")}
    assert under_fs == {"fs.read", "fs.write"}  # db.query NOT included
    assert {t.qualified_name for t in trie.under("db")} == {"db.query"}
    assert trie.under("absent") == []


def test_trie_namespacing_keeps_same_bare_name_distinct():
    # Two mounts exposing the same bare name land at DIFFERENT terminals (no collision).
    trie = ToolTrie()
    trie.insert(ToolSpec(name="read", mount_id="fs"))
    trie.insert(ToolSpec(name="read", mount_id="db"))
    assert len(trie) == 2
    assert {t.qualified_name for t in trie.all_specs()} == {"fs.read", "db.read"}


def test_trie_terminal_collision_goes_to_reject_policy():
    # SAME qualified name twice (same mount + tool) is a genuine terminal collision; the
    # strict policy refuses it. This is the deterministic conflict decision point.
    trie = ToolTrie(conflict_policy=RejectOnConflict())
    trie.insert(ToolSpec(name="read", mount_id="fs"))
    with pytest.raises(MountConflictError, match="fs.read"):
        trie.insert(ToolSpec(name="read", mount_id="fs"))


def test_default_policy_idempotent_remount_keeps_one_terminal():
    # Default NamespaceByMountId resolves a same-name terminal collision by last-writer-wins
    # (idempotent re-mount), never duplicating the terminal.
    trie = ToolTrie()
    trie.insert(ToolSpec(name="read", mount_id="fs"))
    trie.insert(ToolSpec(name="read", mount_id="fs"))
    assert len(trie) == 1
    assert [t.qualified_name for t in trie.all_specs()] == ["fs.read"]


# --- the pending -> active state machine ----------------------------------------------


def test_keystone_mount_is_not_visible_until_next_turn():
    reg = MountRegistry(scope=ACME)
    assert reg.active_tools() == []  # turn 0: nothing active yet

    reg.stage("fs", FakeServer(["read_file"]))
    assert reg.active_tools() == []  # staged (pending) — NOT visible this turn

    reg.begin_turn()  # the safe-turn boundary promotes pending -> active
    assert {t.qualified_name for t in reg.active_tools()} == {"fs.read_file"}


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
    assert {t.qualified_name for t in reg.active_tools()} == {"fs.read", "db.read"}


def test_registry_reject_policy_refuses_duplicate_mount():
    reg = MountRegistry(scope=ACME, conflict_policy=RejectOnConflict())
    reg.stage("fs", FakeServer(["read"]))
    reg.begin_turn()
    reg.stage("fs", FakeServer(["read"]))  # same mount + tool staged again
    with pytest.raises(MountConflictError):
        reg.begin_turn()


def test_registry_tools_under_uses_prefix_walk():
    reg = MountRegistry(scope=ACME)
    reg.stage("fs", FakeServer(["read", "write"]))
    reg.stage("db", FakeServer(["query"]))
    reg.begin_turn()
    assert {t.qualified_name for t in reg.tools_under("fs")} == {"fs.read", "fs.write"}
    assert reg.lookup("db.query") == ToolSpec(name="query", mount_id="db")


def test_reject_conflict_does_not_wedge_future_promotions():
    # ATOMIC begin_turn under RejectOnConflict: a conflicting pending mount is rejected
    # (the policy raises) but the registry must stay CONSISTENT — no leaked partial
    # promotion, _pending emptied — so a LATER good mount still promotes. The old in-place
    # loop left a half-promoted trie + uncleared _pending, permanently wedging promotions.
    fired = []
    reg = MountRegistry(
        scope=ACME,
        conflict_policy=RejectOnConflict(),
        on_invalidate=lambda: fired.append(True),
    )
    # turn 1: a good mount promotes cleanly.
    reg.stage("fs", FakeServer(["read"]))
    reg.begin_turn()
    assert {t.qualified_name for t in reg.active_tools()} == {"fs.read"}
    assert fired == [True]

    # turn 2: a NEW good mount staged alongside a conflicting re-mount of fs.read.
    reg.stage("db", FakeServer(["query"]))  # genuinely new, good
    reg.stage("fs", FakeServer(["read"]))  # duplicate -> RejectOnConflict raises
    with pytest.raises(MountConflictError):
        reg.begin_turn()
    # all-or-nothing: the rejected batch promoted NOTHING — db.query must NOT leak in,
    # and the failed turn fired no invalidation.
    assert {t.qualified_name for t in reg.active_tools()} == {"fs.read"}
    assert fired == [True]

    # turn 3: the wedge proof — a fresh good mount promotes successfully, showing the
    # rejected turn left _pending clear and the trie uncorrupted.
    reg.stage("net", FakeServer(["ping"]))
    reg.begin_turn()
    assert {t.qualified_name for t in reg.active_tools()} == {"fs.read", "net.ping"}
    assert fired == [True, True]


def test_namespace_by_mount_id_is_the_default_policy():
    reg = MountRegistry(scope=ACME)
    assert isinstance(reg.conflict_policy, NamespaceByMountId)


def test_registry_is_tenant_scoped():
    reg = MountRegistry(scope=Scope(tenant_id="acme", namespace="agent:1"))
    assert reg.scope.tenant_id == "acme"
