import pytest

pytest.importorskip("langgraph")

from langgraph.checkpoint.memory import MemorySaver

from coactra.orchestration.workflow import (
    DurableLangGraphEngine,
    Procedure,
    RunContext,
    Scope,
    Step,
    WorkflowEngine,
    WorkflowRunStatus,
)


class RecordingTools:
    def __init__(self) -> None:
        self.calls = []

    async def call(self, *, server, tool, params):
        self.calls.append((server, tool, params))
        return {"ok": True, "tool": tool}


def test_durable_langgraph_engine_satisfies_workflow_engine_protocol():
    assert isinstance(DurableLangGraphEngine(), WorkflowEngine)


@pytest.mark.asyncio
async def test_portable_procedure_interrupts_and_resumes_with_checkpointer():
    engine = DurableLangGraphEngine(
        python_registry={"ship": lambda state: {"shipped": True}},
        checkpointer=MemorySaver(),
    )
    procedure = Procedure(
        name="deploy",
        steps=[
            Step(id="approve", kind="approve", next="ship"),
            Step(id="ship", kind="task"),
        ],
    )
    ctx = RunContext(scope=Scope(tenant_id="acme"))

    paused = await engine.start(
        procedure, {"version": "1.2"}, ctx, thread_id="deploy-1"
    )

    assert paused.status is WorkflowRunStatus.interrupted
    assert paused.thread_id == "acme:deploy-1"
    assert paused.interrupt is not None
    assert paused.interrupt.step_id == "approve"

    completed = await engine.resume(
        "acme:deploy-1",
        ctx,
        procedure=procedure,
        decision={"approved": True},
    )

    assert completed.status is WorkflowRunStatus.completed
    assert completed.result is not None
    assert completed.result.output["shipped"] is True
    assert completed.result.output["approve_decision"] == {"approved": True}


@pytest.mark.asyncio
async def test_rich_document_red_tool_interrupts_before_the_tool_call():
    tools = RecordingTools()
    engine = DurableLangGraphEngine(tool_invoker=tools, checkpointer=MemorySaver())
    doc = {
        "name": "dangerous",
        "nodes": [
            {
                "id": "delete",
                "type": "tool",
                "target": "infra",
                "tool": "delete_vm",
                "inputs": {"vmid": "{{ vmid }}"},
                "tier": "red",
            }
        ],
        "edges": [],
    }

    paused = await engine.run_document(doc, params={"vmid": 42}, thread_id="red-1")

    assert paused["_awaiting_human"] is True
    assert paused["_interrupt"]["approval_required"] is True
    assert tools.calls == []

    final = await engine.run_document(
        doc,
        params={"vmid": 42},
        thread_id="red-1",
        resume="approved",
    )

    assert final["delete_result"] == {"ok": True, "tool": "delete_vm"}
    assert tools.calls == [("infra", "delete_vm", {"vmid": "42"})]


@pytest.mark.asyncio
async def test_sub_procedure_red_gate_interrupts_parent_and_resumes_idempotently():
    # A child sub-procedure whose red-tier node interrupts must pause the PARENT
    # graph (resumable via the parent checkpointer) — not be silently swallowed.
    # The child's green tool BEFORE the gate must run EXACTLY ONCE across the
    # interrupt/resume (never re-executed), and the red tool AFTER approval once.
    tools = RecordingTools()
    child_doc = {
        "name": "child_wipe",
        "nodes": [
            {
                "id": "prep",
                "type": "tool",
                "target": "infra",
                "tool": "snapshot",
                "inputs": {},
                "tier": "green",
            },
            {
                "id": "wipe",
                "type": "tool",
                "target": "infra",
                "tool": "wipe_disk",
                "inputs": {},
                "tier": "red",
            },
        ],
        "edges": [{"from": "prep", "to": "wipe"}],
    }

    async def resolver(name, version=None):
        assert name == "child_wipe"
        return child_doc

    engine = DurableLangGraphEngine(
        tool_invoker=tools,
        checkpointer=MemorySaver(),
        procedure_resolver=resolver,
    )
    parent_doc = {
        "name": "parent",
        "nodes": [{"id": "call_child", "type": "sub-procedure", "procedure": "child_wipe"}],
        "edges": [],
    }

    # First run: child preps, then its red gate must pause the PARENT.
    paused = await engine.run_document(parent_doc, params={}, thread_id="p-1")
    assert paused["_awaiting_human"] is True
    assert tools.calls == [("infra", "snapshot", {})]  # prep ran, wipe gated

    # Resume the parent with approval: child advances past the gate to completion.
    final = await engine.run_document(
        parent_doc, params={}, thread_id="p-1", resume="approved"
    )
    # prep ran EXACTLY ONCE (not re-executed on resume); wipe ran once after approval.
    assert tools.calls == [
        ("infra", "snapshot", {}),
        ("infra", "wipe_disk", {}),
    ]
    assert final["call_child_result"]["wipe_result"] == {"ok": True, "tool": "wipe_disk"}
