import asyncio
from types import SimpleNamespace

from coactra.agent import Scope
from coactra.agent.integrations import make_coactra_agent


class FakeAI:
    def ask(self, prompt):
        return f"answer:{prompt}"

    def structured(self, schema, prompt):
        return schema()


class FakeMemory:
    def __init__(self):
        self.scope = None

    async def remember(self, events, scope):
        self.scope = scope

    async def recall(self, query, scope, k=10):
        self.scope = scope
        return []


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
    def run(self, procedure, state, ctx):
        return {"procedure": procedure, "state": state, "ctx": ctx}


class FakeOrganization:
    def can(self, member, action):
        return True


def test_make_coactra_agent_wires_real_facade_shapes_through_adapters():
    memory = FakeMemory()
    agent = make_coactra_agent(
        scope=Scope(tenant_id="acme", namespace="agent:platform"),
        ai=FakeAI(),
        memory=memory,
        workspace=FakeWorkspace(),
        workflow_engine=FakeWorkflowEngine(),
        workflow_scope="workflow-scope",
        workflow_context_factory=lambda **kwargs: SimpleNamespace(**kwargs),
        organization=FakeOrganization(),
        memory_scope_factory=lambda scope, agent, session: SimpleNamespace(
            tenant=scope.tenant_id, agent=agent or scope.namespace, session=session
        ),
    )

    assert agent.think("hi") == "answer:hi"
    agent.workspace_write("note.md", "hello")
    assert agent.workspace_read("note.md") == "hello"
    assert agent.run_procedure("deploy")["ctx"].collaborator is agent.collaborator

    asyncio.run(agent.remember(["event"]))
    assert memory.scope.tenant == "acme"
    assert memory.scope.agent == "agent:platform"
