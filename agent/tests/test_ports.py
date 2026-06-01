import fleetlib.agent.ports as ports_module
from fleetlib.agent import (
    AIPort,
    FakeAI,
    FakeMemory,
    FakeOrganization,
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


def test_ports_module_does_not_import_sibling_internals():
    # The un-tangling rule: agent consumes siblings through local ports, never their code.
    import inspect

    src = inspect.getsource(ports_module)
    for sibling in ("ai", "memory", "workflow", "workspace", "organization"):
        # catch BOTH `import fleetlib.<sibling>` and `from fleetlib.<sibling> import ...`
        assert f"import fleetlib.{sibling}" not in src
        assert f"from fleetlib.{sibling}" not in src


def test_fake_memory_is_tenant_scoped():
    mem = FakeMemory()
    mem.learn("the build passed", ACME)
    assert mem.recall("build", ACME) == ["the build passed"]
    other = Scope(tenant_id="globex")
    assert mem.recall("build", other) == []  # isolation is real


def test_fake_ai_returns_a_completion():
    assert FakeAI().complete("hello") == "completion:hello"


def test_fake_organization_reports_chain():
    org = FakeOrganization(chain={"agent:a": ["manager", "human"]})
    assert org.escalation_chain("agent:a", ACME) == ["manager", "human"]
