from fleetlib.workflow import (
    LangGraphEngine,
    Procedure,
    ReasoningTrace,
    RunContext,
    Scope,
    Step,
    induce,
    update,
)


def _trace():
    # A captured reasoning path: each entry is one observed action with its id.
    return ReasoningTrace(
        problem="deploy the service",
        steps=[
            {"id": "build", "kind": "task"},
            {"id": "verify", "kind": "task"},
        ],
    )


def test_induce_returns_a_procedure_flagged_as_induced():
    proc = induce(_trace())
    assert isinstance(proc, Procedure)
    assert proc.is_induced is True
    assert [s.id for s in proc.steps] == ["build", "verify"]


def test_induction_is_trace_faithful_and_deterministic():
    # Same trace in -> identical procedure out, every time. No hidden learning.
    a = induce(_trace())
    b = induce(_trace())
    assert a.model_dump() == b.model_dump()


def test_induce_links_steps_linearly_in_trace_order():
    proc = induce(_trace())
    assert proc.step("build").next == "verify"
    assert proc.step("verify").next is None


def test_update_appends_a_step_without_changing_type():
    proc = induce(_trace())
    drifted = ReasoningTrace(
        problem="deploy the service",
        steps=[
            {"id": "build", "kind": "task"},
            {"id": "verify", "kind": "task"},
            {"id": "smoke-test", "kind": "task"},
        ],
    )
    updated = update(proc, drifted)
    assert type(updated) is Procedure
    assert [s.id for s in updated.steps] == ["build", "verify", "smoke-test"]
    assert updated.is_induced is True


def test_does_not_overclaim_learning_update_is_manual():
    # induce/update are pure functions of their inputs. There is NO background relearn:
    # calling induce twice never mutates anything, and update only reflects the trace given.
    proc = induce(_trace())
    same = induce(_trace())
    assert proc.model_dump() == same.model_dump()


# ---- KEYSTONE: induced and authored are the same type AND run the same path ----

def test_keystone_induced_and_authored_run_the_same_path_to_same_result():
    authored = Procedure(
        name="deploy the service",
        steps=[
            Step(id="build", kind="task", next="verify"),
            Step(id="verify", kind="task"),
        ],
    )
    induced = induce(_trace())

    # Same TYPE.
    assert type(authored) is type(induced)

    # Same compile->run PATH on the one engine, identical observable result.
    def make(tag):
        return lambda s: {**s, tag: True}

    eng = LangGraphEngine(tasks={"build": make("build"), "verify": make("verify")})
    ctx = RunContext(scope=Scope(tenant_id="acme"))

    r_auth = eng.run(authored, {}, ctx)
    r_ind = eng.run(induced, {}, ctx)
    assert r_auth.path == r_ind.path == ["build", "verify"]
    assert r_auth.output["build"] and r_ind.output["verify"]
