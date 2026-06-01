from langgraph.graph.state import CompiledStateGraph

from fleetlib.workflow import (
    LangGraphEngine,
    Procedure,
    RunContext,
    Scope,
    Step,
)


def _ctx():
    return RunContext(scope=Scope(tenant_id="acme"))


def test_task_steps_run_registered_callables_in_order():
    seen: list[str] = []

    def make(tag):
        def fn(state):
            seen.append(tag)
            return {**state, tag: True}

        return fn

    eng = LangGraphEngine(tasks={"a": make("a"), "b": make("b")})
    proc = Procedure(
        name="linear",
        steps=[Step(id="a", kind="task", next="b"), Step(id="b", kind="task")],
    )
    result = eng.run(proc, {}, _ctx())
    assert seen == ["a", "b"]
    assert result.output["a"] is True and result.output["b"] is True
    assert result.path == ["a", "b"]


def test_compiled_artifact_is_a_real_langgraph_object():
    # THIN-over-LangGraph conformance: control flow is delegated to LangGraph natives,
    # not a hand-rolled Python interpreter. The compiled artifact must be LangGraph's.
    eng = LangGraphEngine(tasks={"a": lambda s: s})
    proc = Procedure(name="x", steps=[Step(id="a", kind="task")])
    compiled = eng.compile(proc, _ctx())
    assert isinstance(compiled, CompiledStateGraph)


def test_branch_uses_native_conditional_edges():
    def set_ok(state):
        return {**state, "ok": state["want_ok"]}

    eng = LangGraphEngine(
        tasks={
            "decide": set_ok,
            "win": lambda s: {**s, "result": "win"},
            "lose": lambda s: {**s, "result": "lose"},
        }
    )
    proc = Procedure(
        name="branchy",
        steps=[
            Step(id="decide", kind="task", next="gate"),
            Step(
                id="gate",
                kind="branch",
                condition="ok",
                if_true="win",
                if_false="lose",
            ),
            Step(id="win", kind="task"),
            Step(id="lose", kind="task"),
        ],
    )
    won = eng.run(proc, {"want_ok": True}, _ctx())
    lost = eng.run(proc, {"want_ok": False}, _ctx())
    assert won.output["result"] == "win"
    assert lost.output["result"] == "lose"
    assert "win" in won.path and "lose" in lost.path
