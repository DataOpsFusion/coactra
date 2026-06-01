import asyncio
from types import SimpleNamespace

from coactra.agent.integrations import (
    AIAdapter,
    MemoryAdapter,
    OrganizationAdapter,
    WorkflowAdapter,
    WorkspaceAdapter,
)


class FakeAI:
    def ask(self, prompt):
        return f"answer:{prompt}"

    def structured(self, schema, prompt):
        return schema(value=prompt)


class FakeMemory:
    def __init__(self):
        self.calls = []

    async def remember(self, events, scope):
        self.calls.append(("remember", list(events), scope))

    async def recall(self, query, scope, k=10):
        self.calls.append(("recall", query, scope, k))
        return [query]


class FakeWorkspace:
    def __init__(self):
        self.files = {}

    def write(self, path, data):
        self.files[path] = data

    def read(self, path):
        return self.files[path]

    def run(self, command):
        return command


class FakeWorkflowEngine:
    def __init__(self):
        self.ctx = None

    def run(self, procedure, state, ctx):
        self.ctx = ctx
        return {"procedure": procedure, "state": state}


class FakeNode:
    def __init__(self, manager=None):
        self.manager = manager
        self._members = ["ada"]

    def members(self):
        return list(self._members)


class FakeOrganization:
    def can(self, member, action):
        return (member, action) == ("ada", "deploy")


def test_ai_and_workspace_delegate_without_leaking_platform_types():
    ai = AIAdapter(FakeAI())
    assert ai.ask("hi") == "answer:hi"

    workspace = WorkspaceAdapter(FakeWorkspace())
    workspace.write("note.md", "hello")
    assert workspace.read("note.md") == "hello"
    assert workspace.run(["pwd"]) == ["pwd"]


def test_memory_translates_agent_scope_explicitly():
    memory = FakeMemory()
    made = []

    def scope_factory(scope, agent, session):
        translated = SimpleNamespace(tenant=scope.tenant_id, agent=agent or scope.namespace, session=session)
        made.append(translated)
        return translated

    adapter = MemoryAdapter(memory, session="run-1", scope_factory=scope_factory)
    agent_scope = SimpleNamespace(tenant_id="acme", namespace="agent:platform")

    async def scenario():
        await adapter.remember(["event"], agent_scope)
        return await adapter.recall("event", agent_scope, 3)

    assert asyncio.run(scenario()) == ["event"]
    assert [(s.tenant, s.agent, s.session) for s in made] == [
        ("acme", "agent:platform", "run-1"),
        ("acme", "agent:platform", "run-1"),
    ]


def test_workflow_binds_context_and_can_receive_agent_collaboration():
    engine = FakeWorkflowEngine()
    adapter = WorkflowAdapter(
        engine,
        scope="workflow-scope",
        chain=["lead", "human"],
        context_factory=lambda **kwargs: SimpleNamespace(**kwargs),
    )
    collaborator = object()
    adapter.set_collaboration(collaborator)

    assert adapter.run("deploy", {"host": "web1"}) == {
        "procedure": "deploy",
        "state": {"host": "web1"},
    }
    assert engine.ctx.scope == "workflow-scope"
    assert engine.ctx.collaborator is collaborator
    assert engine.ctx.router is collaborator
    assert engine.ctx.chain == ["lead", "human"]


def test_organization_adapts_property_based_manager_api():
    root = FakeOrganization()
    manager = FakeNode()
    node = FakeNode(manager=manager)
    adapter = OrganizationAdapter(root)

    assert adapter.can("ada", "deploy") is True
    assert adapter.members(node) == ["ada"]
    assert adapter.manager(node) is manager
