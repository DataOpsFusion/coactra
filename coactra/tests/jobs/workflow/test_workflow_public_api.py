import pytest

pytest.importorskip("langgraph")

import coactra.jobs.workflow as w


def test_public_surface_is_complete():
    expected = {
        "__version__",
        "Scope",
        "Step",
        "Procedure",
        "RunResult",
        "RunContext",
        "WorkflowEngine",
        "make_workflow_engine",
        "make_default_workflow_engine",
        "WorkflowRuntime",
        "ToolInvoker",
        "LangGraphEngine",
        "DurableLangGraphEngine",
        "build_graph",
        "run_workflow",
        "document_from_procedure",
        "check_done_criteria",
        "ReasoningTrace",
        "induce",
        "update",
        "Approver",
        "Collaborator",
        "EscalationRouter",
        "Escalation",
        "EscalationUnresolved",
        "AutoApprove",
        "RejectAll",
        "NullCollaborator",
        "TerminalHumanRouter",
        "ProcedureStore",
        "InMemoryProcedureStore",
    }
    assert expected <= set(w.__all__)
    for name in expected:
        assert hasattr(w, name), name


def test_end_to_end_author_run_store_and_induce_run():
    scope = w.Scope(tenant_id="acme", namespace="agent:1")

    def make(tag):
        return lambda s: {**s, tag: True}

    eng = w.LangGraphEngine(tasks={"build": make("build"), "verify": make("verify")})
    ctx = w.RunContext(scope=scope)

    # authored -> run -> store -> reuse
    authored = w.Procedure(
        name="deploy",
        steps=[
            w.Step(id="build", kind="task", next="verify"),
            w.Step(id="verify", kind="task"),
        ],
    )
    r1 = eng.run(authored, {}, ctx)
    assert r1.path == ["build", "verify"]

    store = w.InMemoryProcedureStore()
    store.save(authored, scope)
    assert store.get("deploy", scope).name == "deploy"

    # induced from a trace -> SAME run path as authored
    induced = w.induce(
        w.ReasoningTrace(
            problem="deploy",
            steps=[{"id": "build", "kind": "task"}, {"id": "verify", "kind": "task"}],
        )
    )
    r2 = eng.run(induced, {}, ctx)
    assert r2.path == r1.path
    assert induced.is_induced is True
