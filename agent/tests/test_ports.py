import asyncio
import inspect

import coactra.agent.ports as ports_pkg
from coactra.agent import (
    AIPort,
    FakeAI,
    FakeMember,
    FakeMemory,
    FakeOrganization,
    FakeOrgNode,
    FakeWorkflow,
    FakeWorkspace,
    MemoryPort,
    OrganizationPort,
    Scope,
    WorkflowPort,
    WorkspacePort,
)

ACME = Scope(tenant_id="acme")


def test_fakes_satisfy_their_ports():
    assert isinstance(FakeAI(), AIPort)
    assert isinstance(FakeMemory(), MemoryPort)
    assert isinstance(FakeWorkspace(), WorkspacePort)
    assert isinstance(FakeWorkflow(), WorkflowPort)
    assert isinstance(FakeOrganization(), OrganizationPort)


def test_ports_package_does_not_import_sibling_internals():
    # The un-tangling rule: agent consumes siblings through local ports, never their code.
    # Source-check the WHOLE ports package (protocols + fakes), not just one module.
    for module in (ports_pkg, *_submodules(ports_pkg)):
        src = inspect.getsource(module)
        for sibling in ("ai", "memory", "workflow", "workspace", "organization"):
            assert f"import coactra.{sibling}" not in src
            assert f"from coactra.{sibling}" not in src


def _submodules(pkg):
    import importlib
    import pkgutil

    mods = []
    for info in pkgutil.iter_modules(pkg.__path__, pkg.__name__ + "."):
        mods.append(importlib.import_module(info.name))
    return mods


# --- AIPort (mirrors coactra.ai.ask / .structured) -----------------------------------


def test_fake_ai_ask_returns_a_completion():
    assert FakeAI().ask("hello") == "completion:hello"


def test_fake_ai_structured_builds_the_schema():
    from pydantic import BaseModel

    class Decision(BaseModel):
        verdict: str = "ok"

    out = FakeAI().structured(Decision, "decide")
    assert isinstance(out, Decision)
    assert out.verdict == "ok"


# --- MemoryPort (ASYNC — mirrors coactra.memory.remember / .recall) -------------------


def test_fake_memory_is_async_and_tenant_scoped():
    mem = FakeMemory()

    async def scenario():
        await mem.remember(["the build passed"], ACME)
        here = await mem.recall("build", ACME)
        other = await mem.recall("build", Scope(tenant_id="globex"))
        return here, other

    here, other = asyncio.run(scenario())
    assert [r["text"] for r in here] == ["the build passed"]
    assert other == []  # isolation is real across tenants


def test_fake_memory_recall_honors_k():
    mem = FakeMemory()

    async def scenario():
        await mem.remember([f"event-{i}" for i in range(5)], ACME)
        return await mem.recall("event", ACME, k=2)

    hits = asyncio.run(scenario())
    assert len(hits) == 2


# --- WorkspacePort (mirrors Workspace.read/write/run) ---------------------------------


def test_fake_workspace_read_write_run():
    ws = FakeWorkspace(scope=ACME)
    ws.write("notes.md", "hello")
    assert ws.read("notes.md") == "hello"
    assert ws.read("missing.md") == ""
    result = ws.run("ls -la")
    assert result["argv"] == ["ls", "-la"]
    assert result["exit_code"] == 0


# --- WorkflowPort (mirrors workflow run(procedure, state)) ----------------------------


def test_fake_workflow_runs_and_echoes_state():
    out = FakeWorkflow().run("deploy", {"host": "web1"})
    assert out == {"procedure": "deploy", "state": {"host": "web1"}, "ran": True}


# --- OrganizationPort (mirrors Organization.can/members/manager) -----------------------


def test_fake_organization_can_resolves_inherited_grants():
    org = FakeOrganization()
    root = FakeOrgNode(name="acme")
    eng = root.add_child("engineering")
    alice = eng.hire("alice", permissions={"read_logs"})

    # own seat permission
    assert org.can(alice, "read_logs") is True
    # not granted anywhere
    assert org.can(alice, "delete_prod") is False
    # grant at the root inherits DOWN to the member's node
    root.grant("delete_prod")
    assert org.can(alice, "delete_prod") is True


def test_fake_organization_members_and_manager():
    org = FakeOrganization()
    root = FakeOrgNode(name="acme")
    eng = root.add_child("engineering")
    a = eng.hire("alice")
    b = eng.hire("bob")
    assert {m.name for m in org.members(eng)} == {"alice", "bob"}
    assert isinstance(a, FakeMember) and isinstance(b, FakeMember)
    # manager(node) is the parent OU; the root has no manager
    assert org.manager(eng) is root
    assert org.manager(root) is None
