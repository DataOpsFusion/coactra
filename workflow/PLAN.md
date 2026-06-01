# coactra.workflow Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Ship a publishable, thin workflow layer where a **procedure is a data structure** — an *authored* flow and a *learned/induced* flow are the **same type** and run the **same** compile→run path on a durable engine (default **LangGraph**). Bolt on an AWM-style online induction loop (`induce(trace) → Procedure` + a manual `update()` hook) and make collaboration/escalation first-class steps (`ask` another agent, `escalate` up the org until a decider resolves it) — without re-implementing the engine, the org, or the agent wire.

**Architecture:** A `Procedure` is an ordered list of typed `Step`s (`task / branch / approve / ask / escalate`) — pydantic, runtime-editable. The `WorkflowEngine` `typing.Protocol` has exactly ONE working default: `LangGraphEngine`, which **delegates control flow to LangGraph natives** (`task`→node, `branch`→`add_conditional_edges`, then `.compile()`/`.invoke()`) — it never re-implements branching in a Python `for` loop, and a conformance test asserts the compiled artifact is a real LangGraph `CompiledStateGraph`. The keystone property (and the answer to the open research risk "is online learned control-flow bolt-on-able, or does it fork the engine?") is: **bolt-on-able, because the procedure is data** — `induce(trace)` produces a `Procedure` of the *same type* an author writes, the engine recompiles it, and runtime never touches LangGraph internals. `approve`/`ask`/`escalate` call **injected handler Protocols** (`Approver` / `Collaborator` / `EscalationRouter`) rather than baking in `interrupt()` or org/A2A logic — `workflow` owns *when/what*, `organization` routes *who/up-to-whom*, `agent` carries the *talk*. `Scope` (tenant_id + namespace) is mandatory on every run and threads through the store; isolation is real. Induction is **trace-faithful and deterministic; `update()` is manual; there is no auto-relearn** — we do not overclaim self-learning.

**Tech Stack:** Python 3.12+, pydantic v2, langgraph, hatchling (PEP 420 namespace package `coactra/workflow/`, src layout), pytest. The lib-ai dependency is deliberately NOT hard: `induce()` accepts a **local** minimal `ReasoningTrace` shape (own pydantic model), never a `coactra.ai` import — real coactra.ai interop is an agent-layer wiring concern. Optional extras: `temporal` / `prefect` (stub adapters that raise on use, mirroring the sibling memory plan).

---

## File Structure

| File | Single responsibility |
|------|----------------------|
| `pyproject.toml` | Distribution `coactra-workflow`; hatchling targets the `coactra` namespace dir; runtime deps `pydantic`, `langgraph`; `[project.optional-dependencies]` for `temporal`/`prefect`/`dev`. |
| `src/coactra/workflow/__init__.py` | Public API surface — re-exports `Scope`, `Step`, `Procedure`, `RunResult`, `WorkflowEngine`, `LangGraphEngine`, `ReasoningTrace`, `induce`, `Approver`, `Collaborator`, `EscalationRouter`, `Escalation`, `EscalationUnresolved`, `AutoApprove`, `RejectAll`, `TerminalHumanRouter`, `NullCollaborator`, `ProcedureStore`, `InMemoryProcedureStore`. NO `src/coactra/__init__.py` (namespace package). |
| `src/coactra/workflow/py.typed` | PEP 561 typing marker. |
| `src/coactra/workflow/scope.py` | `Scope` value object — `tenant_id` + `namespace`; the multi-tenant key threaded through runs and the store. |
| `src/coactra/workflow/models.py` | `Step` (typed: `task`/`branch`/`approve`/`ask`/`escalate`), `Procedure` (ordered steps; `is_induced` flag), `RunResult`. The ONE shape shared by authored AND induced flows. |
| `src/coactra/workflow/handlers.py` | The injected-Protocol seams: `Approver`, `Collaborator`, `EscalationRouter` Protocols + `Escalation`/`EscalationUnresolved` types + trivial honest defaults (`AutoApprove`, `RejectAll`, `NullCollaborator`, `TerminalHumanRouter`). |
| `src/coactra/workflow/engine.py` | `WorkflowEngine` Protocol + `RunContext` (carries scope + handlers). The swap seam. |
| `src/coactra/workflow/langgraph_engine.py` | `LangGraphEngine` — the ONE working default. Compiles a `Procedure` into a real LangGraph `StateGraph` (task→node, branch→conditional edges, approve/ask/escalate→handler-calling nodes), `.compile()`/`.invoke()`. |
| `src/coactra/workflow/induction.py` | `ReasoningTrace` (local minimal shape) + `induce(trace) → Procedure` (AWM-style, trace-faithful, deterministic) + `update(procedure, trace)` manual hook. |
| `src/coactra/workflow/store.py` | `ProcedureStore` Protocol + `InMemoryProcedureStore` — tenant-scoped save/get/list. The "reuse the flow" half; save/get/list only. |
| `src/coactra/workflow/adapters/__init__.py` | Adapters subpackage marker. |
| `src/coactra/workflow/adapters/_stub.py` | `MissingExtraError` + `require_extra()` helper for optional-extra import guards. |
| `src/coactra/workflow/adapters/temporal.py` | `TemporalEngine` stub — declares it satisfies the engine seam; raises `MissingExtraError` until the `temporal` extra + impl land. |
| `src/coactra/workflow/adapters/prefect.py` | `PrefectEngine` stub — raises until the `prefect` extra. |
| `tests/test_packaging.py` | Asserts `import coactra.workflow` works and `coactra` is a PEP 420 namespace package. |
| `tests/test_scope.py` | `Scope` equality/hashing/validation/key. |
| `tests/test_models.py` | Step typing, Procedure shape, authored vs induced are the same type. |
| `tests/test_langgraph_engine.py` | Authored procedure runs; compiled artifact is a real LangGraph `CompiledStateGraph`; branch uses native conditional edges. |
| `tests/test_induction.py` | `induce(trace)` → Procedure; **keystone**: induced and authored run the SAME path to identical result; induction does not overclaim learning. |
| `tests/test_handlers.py` | `approve` gate (auto/reject), `ask` collaborator, `escalate` walks the injected router to a decider / raises `EscalationUnresolved`; no org logic inside workflow. |
| `tests/test_store.py` | Tenant-scoped save/get/list; tenant A cannot read tenant B's procedures. |
| `tests/test_adapter_stubs.py` | Temporal/Prefect stubs raise `MissingExtraError`. |
| `tests/test_public_api.py` | Public surface lock + end-to-end author→run + induce→run. |

---

## Task 1: Package scaffold (namespace package + importable)

**Files:**
- Create: `pyproject.toml`
- Create: `src/coactra/workflow/__init__.py`
- Create: `src/coactra/workflow/py.typed`
- Test: `tests/test_packaging.py`

- [ ] **Step 1: Write the failing test**

```python
# tests/test_packaging.py
import importlib


def test_workflow_imports():
    mod = importlib.import_module("coactra.workflow")
    assert mod.__name__ == "coactra.workflow"


def test_coactra_is_namespace_package():
    import coactra

    # PEP 420 namespace packages have no __file__ and a virtual __path__.
    assert getattr(coactra, "__file__", None) is None
    assert hasattr(coactra, "__path__")
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/test_packaging.py -v`
Expected: FAIL with `ModuleNotFoundError: No module named 'coactra'`

- [ ] **Step 3: Write minimal implementation**

```toml
# pyproject.toml
[build-system]
requires = ["hatchling"]
build-backend = "hatchling.build"

[project]
name = "coactra-workflow"
version = "0.1.0"
description = "Thin, learnable workflow layer over a durable engine (LangGraph) for AI agent fleets — procedure-as-data, induced or authored, with collaboration + escalation steps."
readme = "README.md"
requires-python = ">=3.12"
license = { text = "MIT" }
dependencies = ["pydantic>=2.7", "langgraph>=0.2"]

[project.optional-dependencies]
temporal = ["temporalio>=1.7"]
prefect = ["prefect>=3"]
dev = ["pytest>=8"]

[tool.hatch.build.targets.wheel]
# PEP 420 namespace: ship the coactra/ dir WITHOUT a top-level coactra/__init__.py
packages = ["src/coactra"]

[tool.hatch.build.targets.sdist]
include = ["src/coactra", "README.md", "tests"]
```

```python
# src/coactra/workflow/__init__.py
"""coactra.workflow — a thin, learnable workflow layer over a durable engine.

A Procedure is a DATA STRUCTURE: an authored flow and an induced (learned) flow are the
SAME type and run the SAME compile->run path on the default LangGraph engine. Steps may
collaborate (ask another agent) or escalate up the org until a decider resolves it.
workflow owns when/what; organization routes who; agent carries the talk. Induction is
trace-faithful and deterministic; update() is manual — we do NOT overclaim self-learning.
"""

__all__ = [
    "__version__",
]

__version__ = "0.1.0"
```

```text
# src/coactra/workflow/py.typed
```

(Do NOT create `src/coactra/__init__.py` — its absence is what makes `coactra` a namespace package.)

- [ ] **Step 4: Run test to verify it passes**

Run: `pip install -e . && pytest tests/test_packaging.py -v`
Expected: PASS (2 passed)

- [ ] **Step 5: Commit**

```bash
git add pyproject.toml src/coactra/workflow/__init__.py src/coactra/workflow/py.typed tests/test_packaging.py
git commit -m "feat(workflow): namespace package scaffold + importable surface"
```

---

## Task 2: Scope — the mandatory multi-tenant key

**Files:**
- Create: `src/coactra/workflow/scope.py`
- Modify: `src/coactra/workflow/__init__.py`
- Test: `tests/test_scope.py`

- [ ] **Step 1: Write the failing test**

```python
# tests/test_scope.py
import pytest
from pydantic import ValidationError

from coactra.workflow import Scope


def test_scope_default_namespace():
    s = Scope(tenant_id="acme")
    assert s.tenant_id == "acme"
    assert s.namespace == "default"


def test_scope_is_hashable_and_equal():
    a = Scope(tenant_id="acme", namespace="agent:1")
    b = Scope(tenant_id="acme", namespace="agent:1")
    assert a == b
    assert hash(a) == hash(b)
    assert {a, b} == {a}


def test_scope_rejects_empty_tenant():
    with pytest.raises(ValidationError):
        Scope(tenant_id="")


def test_scope_key_is_stable_string():
    assert Scope(tenant_id="acme", namespace="agent:1").key == "acme/agent:1"
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/test_scope.py -v`
Expected: FAIL with `ImportError: cannot import name 'Scope'`

- [ ] **Step 3: Write minimal implementation**

```python
# src/coactra/workflow/scope.py
"""Scope — the tenant-scoped key threaded through every run and the procedure store.

Defined LOCALLY (these are standalone distributions; no cross-library import). Same shape
as the sibling libraries: tenant_id + namespace. Isolation is first-class — nothing
crosses a (tenant_id, namespace) boundary unless code explicitly moves it.
"""

from __future__ import annotations

from pydantic import BaseModel, Field


class Scope(BaseModel):
    """Immutable, hashable tenant + namespace key."""

    model_config = {"frozen": True}

    tenant_id: str = Field(min_length=1)
    namespace: str = Field(default="default", min_length=1)

    @property
    def key(self) -> str:
        return f"{self.tenant_id}/{self.namespace}"
```

```python
# src/coactra/workflow/__init__.py  (extend imports + __all__)
from coactra.workflow.scope import Scope

__all__ = [
    "__version__",
    "Scope",
]
```

- [ ] **Step 4: Run test to verify it passes**

Run: `pytest tests/test_scope.py -v`
Expected: PASS (4 passed)

- [ ] **Step 5: Commit**

```bash
git add src/coactra/workflow/scope.py src/coactra/workflow/__init__.py tests/test_scope.py
git commit -m "feat(workflow): Scope — mandatory multi-tenant key (tenant_id + namespace)"
```

---

## Task 3: Models — Step, Procedure, RunResult (authored == induced shape)

**Files:**
- Create: `src/coactra/workflow/models.py`
- Modify: `src/coactra/workflow/__init__.py`
- Test: `tests/test_models.py`

- [ ] **Step 1: Write the failing test**

```python
# tests/test_models.py
import pytest
from pydantic import ValidationError

from coactra.workflow import Procedure, RunResult, Step


def test_task_step_minimal():
    s = Step(id="deploy", kind="task")
    assert s.kind == "task"
    assert s.id == "deploy"
    assert s.next is None


def test_branch_step_requires_condition_and_targets():
    s = Step(
        id="check",
        kind="branch",
        condition="ok",  # flat state key — the LangGraphEngine selector does state.get("ok")
        if_true="done",
        if_false="rollback",
    )
    assert s.if_true == "done"
    assert s.if_false == "rollback"


def test_branch_without_condition_is_rejected():
    with pytest.raises(ValidationError):
        Step(id="check", kind="branch", if_true="a", if_false="b")


def test_ask_step_carries_target_agent_and_question():
    s = Step(id="consult", kind="ask", agent="security", question="is this safe?", next="apply")
    assert s.agent == "security"
    assert s.question == "is this safe?"


def test_procedure_is_ordered_and_indexed_by_id():
    p = Procedure(
        name="deploy-flow",
        steps=[Step(id="a", kind="task", next="b"), Step(id="b", kind="task")],
    )
    assert [s.id for s in p.steps] == ["a", "b"]
    assert p.step("b").id == "b"
    assert p.entry.id == "a"


def test_authored_and_induced_are_the_same_type():
    authored = Procedure(name="x", steps=[Step(id="a", kind="task")])
    induced = Procedure(name="x", steps=[Step(id="a", kind="task")], is_induced=True)
    assert type(authored) is type(induced)
    assert authored.is_induced is False
    assert induced.is_induced is True


def test_run_result_holds_path_and_output():
    r = RunResult(output={"ok": True}, path=["a", "b"])
    assert r.output == {"ok": True}
    assert r.path == ["a", "b"]
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/test_models.py -v`
Expected: FAIL with `ImportError: cannot import name 'Procedure'`

- [ ] **Step 3: Write minimal implementation**

```python
# src/coactra/workflow/models.py
"""Procedure-as-data models.

A Procedure is an ordered list of typed Steps. The SAME type is used whether a human
authored the flow or induce() learned it from a trace (is_induced just records origin).
Step kinds are deliberately few: task / branch / approve / ask / escalate.
"""

from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel, Field, model_validator

StepKind = Literal["task", "branch", "approve", "ask", "escalate"]


class Step(BaseModel):
    """One node in a Procedure.

    task     — do work (the engine invokes the registered callable for this id).
    branch   — `condition` is a flat state key; truthy -> if_true, else if_false.
               (The default LangGraphEngine does `bool(state.get(condition))`. A richer
               expression evaluator is a future engine concern, not v1.)
    approve  — pause for an Approver decision (human gate).
    ask      — collaborate: ask another `agent` (a Collaborator handles the talk).
    escalate — raise up the org via an EscalationRouter until a decider resolves it.
    """

    id: str = Field(min_length=1)
    kind: StepKind
    next: str | None = None  # linear successor for non-branch steps (None = terminal)

    # branch-only
    condition: str | None = None
    if_true: str | None = None
    if_false: str | None = None

    # ask-only
    agent: str | None = None
    question: str | None = None  # what to ask the agent (falls back to a state dump if unset)

    # escalate-only
    reason: str | None = None

    @model_validator(mode="after")
    def _validate_kind(self) -> "Step":
        if self.kind == "branch":
            if not self.condition or self.if_true is None or self.if_false is None:
                raise ValueError("branch step requires condition, if_true, if_false")
        if self.kind == "ask" and not self.agent:
            raise ValueError("ask step requires an agent")
        return self


class Procedure(BaseModel):
    """An ordered, runnable, runtime-editable flow. Authored and induced share this type."""

    name: str = Field(min_length=1)
    steps: list[Step] = Field(min_length=1)
    is_induced: bool = False

    @property
    def entry(self) -> Step:
        return self.steps[0]

    def step(self, step_id: str) -> Step:
        for s in self.steps:
            if s.id == step_id:
                return s
        raise KeyError(step_id)


class RunResult(BaseModel):
    """Outcome of one engine run: final state output + the step ids actually visited."""

    output: dict[str, Any] = Field(default_factory=dict)
    path: list[str] = Field(default_factory=list)
```

```python
# src/coactra/workflow/__init__.py  (extend imports + __all__)
from coactra.workflow.models import Procedure, RunResult, Step
from coactra.workflow.scope import Scope

__all__ = [
    "__version__",
    "Scope",
    "Step",
    "Procedure",
    "RunResult",
]
```

- [ ] **Step 4: Run test to verify it passes**

Run: `pytest tests/test_models.py -v`
Expected: PASS (7 passed)

- [ ] **Step 5: Commit**

```bash
git add src/coactra/workflow/models.py src/coactra/workflow/__init__.py tests/test_models.py
git commit -m "feat(workflow): Step/Procedure/RunResult — one shape for authored + induced flows"
```

---

## Task 4: Handlers — the injected escalation/collaboration/approval seams

**Files:**
- Create: `src/coactra/workflow/handlers.py`
- Modify: `src/coactra/workflow/__init__.py`
- Test: `tests/test_handlers.py`

- [ ] **Step 1: Write the failing test**

```python
# tests/test_handlers.py
import pytest

from coactra.workflow import (
    Approver,
    AutoApprove,
    Collaborator,
    Escalation,
    EscalationRouter,
    EscalationUnresolved,
    NullCollaborator,
    RejectAll,
    TerminalHumanRouter,
)


def test_default_approver_protocols_are_runtime_checkable():
    assert isinstance(AutoApprove(), Approver)
    assert isinstance(RejectAll(), Approver)
    assert isinstance(NullCollaborator(), Collaborator)
    assert isinstance(TerminalHumanRouter(), EscalationRouter)


def test_auto_approve_and_reject_all():
    assert AutoApprove().approve("deploy", {"x": 1}) is True
    assert RejectAll().approve("deploy", {"x": 1}) is False


def test_null_collaborator_echoes_a_recorded_answer():
    c = NullCollaborator(answers={"security": "looks fine"})
    assert c.ask("security", "is this safe?", {}) == "looks fine"


def test_terminal_human_router_resolves_at_the_human():
    router = TerminalHumanRouter()
    esc = Escalation(reason="cannot decide", state={"k": 1})
    decision = router.route(esc, chain=["manager", "human"])
    assert decision == "human"  # walked up to the terminal decider


def test_router_raises_when_chain_has_no_decider():
    router = TerminalHumanRouter()
    esc = Escalation(reason="stuck", state={})
    with pytest.raises(EscalationUnresolved):
        router.route(esc, chain=[])
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/test_handlers.py -v`
Expected: FAIL with `ImportError: cannot import name 'Approver'`

- [ ] **Step 3: Write minimal implementation**

```python
# src/coactra/workflow/handlers.py
"""The injected seams for the three non-task step kinds.

workflow owns WHEN/WHAT (it raises these and calls these handlers); it does NOT own who
the chain is (organization) or how the talk happens (agent). So approve/ask/escalate are
Protocols with trivial, honest in-process defaults. Swap in real org routing / A2A talk /
interrupt()-based human gates at the agent layer.
"""

from __future__ import annotations

from typing import Any, Protocol, runtime_checkable

from pydantic import BaseModel, Field


class EscalationUnresolved(RuntimeError):
    """Raised when an escalation reaches the top of the chain without a decider."""


class Escalation(BaseModel):
    """A workflow's signal that it cannot decide on its own and must go up the org."""

    reason: str
    state: dict[str, Any] = Field(default_factory=dict)


@runtime_checkable
class Approver(Protocol):
    def approve(self, step_id: str, state: dict[str, Any]) -> bool:
        """Decide whether an `approve` step may proceed."""
        ...


@runtime_checkable
class Collaborator(Protocol):
    def ask(self, agent: str, question: str, state: dict[str, Any]) -> str:
        """Carry an `ask` step to another agent and return its answer."""
        ...


@runtime_checkable
class EscalationRouter(Protocol):
    def route(self, escalation: Escalation, chain: list[str]) -> str:
        """Walk an escalation UP `chain` and return the id of the decider that resolved it."""
        ...


class AutoApprove:
    """Default Approver — green-lights everything (for tests / fully-trusted flows)."""

    def approve(self, step_id: str, state: dict[str, Any]) -> bool:
        return True


class RejectAll:
    """Default Approver alt — denies everything (proves the gate actually gates)."""

    def approve(self, step_id: str, state: dict[str, Any]) -> bool:
        return False


class NullCollaborator:
    """Default Collaborator — returns a pre-recorded answer per agent; no real wire."""

    def __init__(self, answers: dict[str, str] | None = None) -> None:
        self._answers = answers or {}

    def ask(self, agent: str, question: str, state: dict[str, Any]) -> str:
        return self._answers.get(agent, "")


class TerminalHumanRouter:
    """Default EscalationRouter — the chain is opaque to workflow; this just takes the
    LAST id in the provided chain as the terminal decider (human / SOTA). Real hierarchy
    walking lives in `organization`; workflow holds NO org logic of its own."""

    def route(self, escalation: Escalation, chain: list[str]) -> str:
        if not chain:
            raise EscalationUnresolved(escalation.reason)
        return chain[-1]
```

```python
# src/coactra/workflow/__init__.py  (extend imports + __all__)
from coactra.workflow.handlers import (
    Approver,
    AutoApprove,
    Collaborator,
    Escalation,
    EscalationRouter,
    EscalationUnresolved,
    NullCollaborator,
    RejectAll,
    TerminalHumanRouter,
)
from coactra.workflow.models import Procedure, RunResult, Step
from coactra.workflow.scope import Scope

__all__ = [
    "__version__",
    "Scope",
    "Step",
    "Procedure",
    "RunResult",
    "Approver",
    "Collaborator",
    "EscalationRouter",
    "Escalation",
    "EscalationUnresolved",
    "AutoApprove",
    "RejectAll",
    "NullCollaborator",
    "TerminalHumanRouter",
]
```

- [ ] **Step 4: Run test to verify it passes**

Run: `pytest tests/test_handlers.py -v`
Expected: PASS (5 passed)

- [ ] **Step 5: Commit**

```bash
git add src/coactra/workflow/handlers.py src/coactra/workflow/__init__.py tests/test_handlers.py
git commit -m "feat(workflow): Approver/Collaborator/EscalationRouter Protocols + honest defaults"
```

---

## Task 5: WorkflowEngine Protocol + RunContext (the swap seam)

**Files:**
- Create: `src/coactra/workflow/engine.py`
- Modify: `src/coactra/workflow/__init__.py`
- Test: `tests/test_engine_protocol.py`

- [ ] **Step 1: Write the failing test**

```python
# tests/test_engine_protocol.py
from coactra.workflow import (
    AutoApprove,
    NullCollaborator,
    Procedure,
    RunResult,
    Scope,
    Step,
    TerminalHumanRouter,
    WorkflowEngine,
)
from coactra.workflow.engine import RunContext


def _ctx():
    return RunContext(
        scope=Scope(tenant_id="acme"),
        approver=AutoApprove(),
        collaborator=NullCollaborator(),
        router=TerminalHumanRouter(),
        chain=["human"],
    )


class _Dummy:
    def run(self, procedure, state, ctx):
        return RunResult(output=state, path=[s.id for s in procedure.steps])


def test_engine_protocol_is_runtime_checkable():
    assert isinstance(_Dummy(), WorkflowEngine)


def test_incomplete_class_is_not_an_engine():
    class Partial:
        pass

    assert not isinstance(Partial(), WorkflowEngine)


def test_run_context_defaults_are_filled_in():
    ctx = RunContext(scope=Scope(tenant_id="acme"))
    assert isinstance(ctx.approver, AutoApprove)
    assert isinstance(ctx.router, TerminalHumanRouter)
    assert ctx.chain == []


def test_dummy_engine_runs_via_context():
    p = Procedure(name="x", steps=[Step(id="a", kind="task")])
    out = _Dummy().run(p, {"v": 1}, _ctx())
    assert out.path == ["a"]
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/test_engine_protocol.py -v`
Expected: FAIL with `ImportError: cannot import name 'WorkflowEngine'`

- [ ] **Step 3: Write minimal implementation**

```python
# src/coactra/workflow/engine.py
"""WorkflowEngine — the swappable execution seam, plus the RunContext it consumes.

ONE working default implements this: LangGraphEngine. Temporal/Prefect are stubs. The
RunContext carries the scope (multi-tenant) and the injected handlers so the engine never
hard-codes approval/collaboration/escalation behavior.
"""

from __future__ import annotations

from typing import Any, Protocol, runtime_checkable

from pydantic import BaseModel, Field

from coactra.workflow.handlers import (
    Approver,
    AutoApprove,
    Collaborator,
    EscalationRouter,
    NullCollaborator,
    TerminalHumanRouter,
)
from coactra.workflow.models import Procedure, RunResult
from coactra.workflow.scope import Scope


class RunContext(BaseModel):
    """Everything a run needs beyond the procedure + state: tenant scope and handlers."""

    model_config = {"arbitrary_types_allowed": True}

    scope: Scope
    approver: Approver = Field(default_factory=AutoApprove)
    collaborator: Collaborator = Field(default_factory=NullCollaborator)
    router: EscalationRouter = Field(default_factory=TerminalHumanRouter)
    chain: list[str] = Field(default_factory=list)  # the org chain for escalate steps


@runtime_checkable
class WorkflowEngine(Protocol):
    def run(
        self, procedure: Procedure, state: dict[str, Any], ctx: RunContext
    ) -> RunResult:
        """Compile and execute a procedure within ctx.scope, returning output + path."""
        ...
```

```python
# src/coactra/workflow/__init__.py  (extend imports + __all__)
from coactra.workflow.engine import RunContext, WorkflowEngine
from coactra.workflow.handlers import (
    Approver,
    AutoApprove,
    Collaborator,
    Escalation,
    EscalationRouter,
    EscalationUnresolved,
    NullCollaborator,
    RejectAll,
    TerminalHumanRouter,
)
from coactra.workflow.models import Procedure, RunResult, Step
from coactra.workflow.scope import Scope

__all__ = [
    "__version__",
    "Scope",
    "Step",
    "Procedure",
    "RunResult",
    "RunContext",
    "WorkflowEngine",
    "Approver",
    "Collaborator",
    "EscalationRouter",
    "Escalation",
    "EscalationUnresolved",
    "AutoApprove",
    "RejectAll",
    "NullCollaborator",
    "TerminalHumanRouter",
]
```

- [ ] **Step 4: Run test to verify it passes**

Run: `pytest tests/test_engine_protocol.py -v`
Expected: PASS (4 passed)

- [ ] **Step 5: Commit**

```bash
git add src/coactra/workflow/engine.py src/coactra/workflow/__init__.py tests/test_engine_protocol.py
git commit -m "feat(workflow): WorkflowEngine Protocol + RunContext (scope + injected handlers)"
```

---

## Task 6: LangGraphEngine — compile a Procedure to a real LangGraph StateGraph

**Files:**
- Create: `src/coactra/workflow/langgraph_engine.py`
- Modify: `src/coactra/workflow/__init__.py`
- Test: `tests/test_langgraph_engine.py`

- [ ] **Step 1: Write the failing test**

```python
# tests/test_langgraph_engine.py
from langgraph.graph.state import CompiledStateGraph

from coactra.workflow import (
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
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/test_langgraph_engine.py -v`
Expected: FAIL with `ImportError: cannot import name 'LangGraphEngine'`

- [ ] **Step 3: Write minimal implementation**

```python
# src/coactra/workflow/langgraph_engine.py
"""LangGraphEngine — the ONE working default WorkflowEngine.

Control flow is DELEGATED to LangGraph natives, never re-implemented:
  task     -> a graph node running the registered callable
  branch   -> add_conditional_edges keyed on a CEL-free dict-attribute condition
  approve  -> a node that consults ctx.approver (proceed or stop)
  ask      -> a node that consults ctx.collaborator and records the answer in state
  escalate -> a node that routes ctx.router up ctx.chain to a decider
The compiled artifact is a real langgraph CompiledStateGraph (proven by a conformance
test). __path__ is tracked in state so RunResult can report the steps actually visited.
"""

from __future__ import annotations

from collections.abc import Callable
from typing import Any

from langgraph.graph import END, START, StateGraph

from coactra.workflow.engine import RunContext
from coactra.workflow.handlers import Escalation
from coactra.workflow.models import Procedure, RunResult, Step

TaskFn = Callable[[dict[str, Any]], dict[str, Any]]
_PATH = "__path__"
_STOPPED = "__stopped__"


class LangGraphEngine:
    """Compiles Procedures into LangGraph StateGraphs and runs them."""

    def __init__(self, tasks: dict[str, TaskFn] | None = None) -> None:
        self._tasks = tasks or {}

    # --- node builders ---------------------------------------------------------------

    def _record(self, state: dict[str, Any], step_id: str) -> list[str]:
        return [*state.get(_PATH, []), step_id]

    def _task_node(self, step: Step) -> TaskFn:
        fn = self._tasks.get(step.id, lambda s: s)

        def node(state: dict[str, Any]) -> dict[str, Any]:
            updated = fn(state)
            # Merge over the prior state so a task fn returning a PARTIAL dict never drops
            # keys — correct regardless of whether StateGraph(dict) merges or replaces.
            return {**state, **updated, _PATH: self._record(state, step.id)}

        return node

    def _branch_node(self, step: Step) -> TaskFn:
        def node(state: dict[str, Any]) -> dict[str, Any]:
            return {**state, _PATH: self._record(state, step.id)}

        return node

    def _approve_node(self, step: Step, ctx: RunContext) -> TaskFn:
        def node(state: dict[str, Any]) -> dict[str, Any]:
            ok = ctx.approver.approve(step.id, state)
            return {
                **state,
                _PATH: self._record(state, step.id),
                _STOPPED: not ok,
            }

        return node

    def _ask_node(self, step: Step, ctx: RunContext) -> TaskFn:
        def node(state: dict[str, Any]) -> dict[str, Any]:
            question = step.question or str(state)
            answer = ctx.collaborator.ask(step.agent or "", question, state)
            answers = {**state.get("answers", {}), step.agent: answer}
            return {**state, "answers": answers, _PATH: self._record(state, step.id)}

        return node

    def _escalate_node(self, step: Step, ctx: RunContext) -> TaskFn:
        def node(state: dict[str, Any]) -> dict[str, Any]:
            esc = Escalation(reason=step.reason or step.id, state=state)
            decider = ctx.router.route(esc, ctx.chain)
            return {
                **state,
                "decider": decider,
                _PATH: self._record(state, step.id),
            }

        return node

    # --- compilation -----------------------------------------------------------------

    def compile(self, procedure: Procedure, ctx: RunContext):
        graph: StateGraph = StateGraph(dict)
        builders = {
            "task": self._task_node,
            "branch": self._branch_node,
            "approve": lambda s: self._approve_node(s, ctx),
            "ask": lambda s: self._ask_node(s, ctx),
            "escalate": lambda s: self._escalate_node(s, ctx),
        }
        for step in procedure.steps:
            graph.add_node(step.id, builders[step.kind](step))

        graph.add_edge(START, procedure.entry.id)

        for step in procedure.steps:
            if step.kind == "branch":
                graph.add_conditional_edges(
                    step.id,
                    self._branch_selector(step),
                    {True: step.if_true, False: step.if_false},
                )
            elif step.kind == "approve":
                graph.add_conditional_edges(
                    step.id,
                    lambda state: not state.get(_STOPPED, False),
                    {True: step.next or END, False: END},
                )
            else:
                graph.add_edge(step.id, step.next or END)

        return graph.compile()

    @staticmethod
    def _branch_selector(step: Step):
        attr = step.condition

        def select(state: dict[str, Any]) -> bool:
            return bool(state.get(attr))

        return select

    # --- execution -------------------------------------------------------------------

    def run(
        self, procedure: Procedure, state: dict[str, Any], ctx: RunContext
    ) -> RunResult:
        compiled = self.compile(procedure, ctx)
        final = compiled.invoke({**state, _PATH: []})
        path = final.pop(_PATH, [])
        final.pop(_STOPPED, None)
        return RunResult(output=final, path=path)
```

```python
# src/coactra/workflow/__init__.py  (full file — extend imports + __all__)
from coactra.workflow.engine import RunContext, WorkflowEngine
from coactra.workflow.handlers import (
    Approver,
    AutoApprove,
    Collaborator,
    Escalation,
    EscalationRouter,
    EscalationUnresolved,
    NullCollaborator,
    RejectAll,
    TerminalHumanRouter,
)
from coactra.workflow.langgraph_engine import LangGraphEngine
from coactra.workflow.models import Procedure, RunResult, Step
from coactra.workflow.scope import Scope

__version__ = "0.1.0"

__all__ = [
    "__version__",
    "Scope",
    "Step",
    "Procedure",
    "RunResult",
    "RunContext",
    "WorkflowEngine",
    "LangGraphEngine",
    "Approver",
    "Collaborator",
    "EscalationRouter",
    "Escalation",
    "EscalationUnresolved",
    "AutoApprove",
    "RejectAll",
    "NullCollaborator",
    "TerminalHumanRouter",
]
```

- [ ] **Step 4: Run test to verify it passes**

Run: `pytest tests/test_langgraph_engine.py -v`
Expected: PASS (3 passed)

> **Verify before trusting the suite:** confirm `StateGraph(dict)` (builtin `dict` as the
> state schema) instantiates and `.compile()`s at the pinned `langgraph>=0.2`. If that API
> shape changed, switch to a `TypedDict`/annotated state schema — the node bodies and tests
> stay the same. (The `{**state, **updated}` merge above keeps the engine correct under
> either merge-or-replace state semantics.)

- [ ] **Step 5: Commit**

```bash
git add src/coactra/workflow/langgraph_engine.py src/coactra/workflow/__init__.py tests/test_langgraph_engine.py
git commit -m "feat(workflow): LangGraphEngine — compile Procedure to a real LangGraph StateGraph"
```

---

## Task 7: Handler steps end-to-end through the engine (approve / ask / escalate)

**Files:**
- Test: `tests/test_engine_handlers.py`

(No new implementation — Task 6 wired the handler nodes; this proves they fire through the injected Protocols and that workflow holds no org logic.)

- [ ] **Step 1: Write the failing test**

```python
# tests/test_engine_handlers.py
import pytest

from coactra.workflow import (
    EscalationUnresolved,
    LangGraphEngine,
    Procedure,
    RejectAll,
    RunContext,
    Scope,
    Step,
    TerminalHumanRouter,
)


def _ctx(**kw):
    base = dict(scope=Scope(tenant_id="acme"))
    base.update(kw)
    return RunContext(**base)


def test_approve_reject_stops_before_the_guarded_step():
    ran: list[str] = []
    eng = LangGraphEngine(tasks={"apply": lambda s: ran.append("apply") or s})
    proc = Procedure(
        name="gated",
        steps=[
            Step(id="gate", kind="approve", next="apply"),
            Step(id="apply", kind="task"),
        ],
    )
    result = eng.run(proc, {}, _ctx(approver=RejectAll()))
    assert ran == []  # rejected -> guarded step never ran
    assert "apply" not in result.path


def test_ask_carries_the_question_and_records_the_answer():
    asked: list[tuple[str, str]] = []

    class Recorder:
        def ask(self, agent, question, state):
            asked.append((agent, question))
            return "safe to ship"

    eng = LangGraphEngine(tasks={"done": lambda s: s})
    proc = Procedure(
        name="consult",
        steps=[
            Step(id="consult", kind="ask", agent="security", question="is this safe?", next="done"),
            Step(id="done", kind="task"),
        ],
    )
    result = eng.run(proc, {}, _ctx(collaborator=Recorder()))
    assert asked == [("security", "is this safe?")]  # the step's question reached the agent
    assert result.output["answers"]["security"] == "safe to ship"


def test_escalate_routes_to_terminal_decider():
    eng = LangGraphEngine()
    proc = Procedure(
        name="stuck",
        steps=[Step(id="bump", kind="escalate", reason="cannot decide")],
    )
    ctx = _ctx(router=TerminalHumanRouter(), chain=["manager", "director", "human"])
    result = eng.run(proc, {}, ctx)
    assert result.output["decider"] == "human"


def test_escalate_with_empty_chain_raises_unresolved():
    eng = LangGraphEngine()
    proc = Procedure(
        name="stuck",
        steps=[Step(id="bump", kind="escalate", reason="no chain")],
    )
    with pytest.raises(EscalationUnresolved):
        eng.run(proc, {}, _ctx(chain=[]))


def test_workflow_holds_no_org_logic():
    # The router decides who; workflow only hands it the opaque chain. Proven by the fact
    # that swapping the chain changes the decider with zero workflow code change.
    eng = LangGraphEngine()
    proc = Procedure(name="x", steps=[Step(id="e", kind="escalate")])
    a = eng.run(proc, {}, _ctx(chain=["human"]))
    b = eng.run(proc, {}, _ctx(chain=["sota"]))
    assert a.output["decider"] == "human"
    assert b.output["decider"] == "sota"
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/test_engine_handlers.py -v`
Expected: PASS already IF Task 6 is correct. If any FAIL, the bug is in the handler node wiring — fix `langgraph_engine.py` before proceeding (do not weaken the test).

- [ ] **Step 3: No new implementation**

Handler nodes were built in Task 6. This task locks their end-to-end behavior and the "no org logic" boundary.

- [ ] **Step 4: Run test to confirm green**

Run: `pytest tests/test_engine_handlers.py -v`
Expected: PASS (5 passed)

- [ ] **Step 5: Commit**

```bash
git add tests/test_engine_handlers.py
git commit -m "test(workflow): lock approve/ask/escalate through injected handlers + no-org-logic boundary"
```

---

## Task 8: Induction — trace → Procedure (the AWM-style loop) + the keystone

**Files:**
- Create: `src/coactra/workflow/induction.py`
- Modify: `src/coactra/workflow/__init__.py`
- Test: `tests/test_induction.py`

- [ ] **Step 1: Write the failing test**

```python
# tests/test_induction.py
from coactra.workflow import (
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
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/test_induction.py -v`
Expected: FAIL with `ImportError: cannot import name 'ReasoningTrace'`

- [ ] **Step 3: Write minimal implementation**

```python
# src/coactra/workflow/induction.py
"""AWM-style induction: turn a captured reasoning trace into a reusable Procedure.

HONEST SCOPE (do not overclaim): induce() is a trace-faithful, deterministic projection
of a trace's observed actions into the SAME Procedure data structure an author writes.
update() is a MANUAL hook applied when reality drifts — there is no background relearn,
no statistical generalization here. The novelty is that the output is data, so the engine
runs an induced flow on the exact same compile->run path as an authored one.

ReasoningTrace is a LOCAL minimal shape on purpose: no import of coactra.ai. Real
interop with coactra.ai's richer ReasoningTrace is an agent-layer wiring concern.
"""

from __future__ import annotations

from typing import Any

from pydantic import BaseModel, Field

from coactra.workflow.models import Procedure, Step


class ReasoningTrace(BaseModel):
    """A captured working path: the problem + the ordered actions that solved it.

    Each entry in `steps` is a dict with at least {"id": str, "kind": StepKind} plus any
    step-specific keys (condition/if_true/if_false/agent/reason). Minimal and local.
    """

    problem: str = Field(min_length=1)
    steps: list[dict[str, Any]] = Field(min_length=1)


def _to_steps(raw: list[dict[str, Any]]) -> list[Step]:
    steps: list[Step] = []
    for i, entry in enumerate(raw):
        nxt = raw[i + 1]["id"] if i + 1 < len(raw) and entry.get("kind") != "branch" else None
        # Branch entries carry their own targets; non-branch get the linear successor.
        data = {**entry}
        if entry.get("kind") != "branch" and "next" not in data:
            data["next"] = nxt
        steps.append(Step(**data))
    return steps


def induce(trace: ReasoningTrace) -> Procedure:
    """Project a trace into a runnable, induced Procedure (same type as authored)."""
    return Procedure(
        name=trace.problem,
        steps=_to_steps(trace.steps),
        is_induced=True,
    )


def update(procedure: Procedure, trace: ReasoningTrace) -> Procedure:
    """Manual drift hook: re-induce from a fresh trace, preserving the procedure name.

    Honest and minimal: this is a re-projection, not a merge/diff algorithm. The caller
    decides WHEN reality drifted; update() just produces the new induced Procedure.
    """
    fresh = induce(trace)
    return Procedure(name=procedure.name, steps=fresh.steps, is_induced=True)
```

```python
# src/coactra/workflow/__init__.py  (full file — extend imports + __all__)
from coactra.workflow.engine import RunContext, WorkflowEngine
from coactra.workflow.handlers import (
    Approver,
    AutoApprove,
    Collaborator,
    Escalation,
    EscalationRouter,
    EscalationUnresolved,
    NullCollaborator,
    RejectAll,
    TerminalHumanRouter,
)
from coactra.workflow.induction import ReasoningTrace, induce, update
from coactra.workflow.langgraph_engine import LangGraphEngine
from coactra.workflow.models import Procedure, RunResult, Step
from coactra.workflow.scope import Scope

__version__ = "0.1.0"

__all__ = [
    "__version__",
    "Scope",
    "Step",
    "Procedure",
    "RunResult",
    "RunContext",
    "WorkflowEngine",
    "LangGraphEngine",
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
]
```

- [ ] **Step 4: Run test to verify it passes**

Run: `pytest tests/test_induction.py -v`
Expected: PASS (6 passed)

- [ ] **Step 5: Commit**

```bash
git add src/coactra/workflow/induction.py src/coactra/workflow/__init__.py tests/test_induction.py
git commit -m "feat(workflow): AWM-style induce()/update() — induced flows are the same data, same run path"
```

---

## Task 9: ProcedureStore — tenant-scoped reuse (save / get / list)

**Files:**
- Create: `src/coactra/workflow/store.py`
- Modify: `src/coactra/workflow/__init__.py`
- Test: `tests/test_store.py`

- [ ] **Step 1: Write the failing test**

```python
# tests/test_store.py
import pytest

from coactra.workflow import (
    InMemoryProcedureStore,
    Procedure,
    ProcedureStore,
    Scope,
    Step,
    induce,
)
from coactra.workflow import ReasoningTrace

ACME = Scope(tenant_id="acme", namespace="agent:1")
GLOBEX = Scope(tenant_id="globex", namespace="agent:1")


def _proc(name="deploy"):
    return Procedure(name=name, steps=[Step(id="a", kind="task")])


def test_store_satisfies_protocol():
    assert isinstance(InMemoryProcedureStore(), ProcedureStore)


def test_save_then_get_in_scope():
    store = InMemoryProcedureStore()
    store.save(_proc(), ACME)
    got = store.get("deploy", ACME)
    assert got is not None and got.name == "deploy"


def test_get_missing_returns_none():
    assert InMemoryProcedureStore().get("nope", ACME) is None


def test_list_returns_scope_procedures_only():
    store = InMemoryProcedureStore()
    store.save(_proc("deploy"), ACME)
    store.save(_proc("backup"), ACME)
    names = {p.name for p in store.list(ACME)}
    assert names == {"deploy", "backup"}


def test_tenant_isolation_is_real():
    store = InMemoryProcedureStore()
    store.save(_proc("acme-only"), ACME)
    assert store.get("acme-only", GLOBEX) is None
    assert store.list(GLOBEX) == []


def test_induced_procedure_round_trips_through_the_store():
    store = InMemoryProcedureStore()
    induced = induce(ReasoningTrace(problem="deploy", steps=[{"id": "a", "kind": "task"}]))
    store.save(induced, ACME)
    got = store.get("deploy", ACME)
    assert got is not None and got.is_induced is True
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/test_store.py -v`
Expected: FAIL with `ImportError: cannot import name 'InMemoryProcedureStore'`

- [ ] **Step 3: Write minimal implementation**

```python
# src/coactra/workflow/store.py
"""ProcedureStore — the tenant-scoped library that makes "reuse the flow" real.

Deliberately tiny: save / get / list, keyed by Scope. This is the easy piece to balloon,
so it stays minimal. The ONE working default is in-memory and tenant-isolated; swap in a
durable backend (CouchDB / Postgres) behind the same Protocol later.
"""

from __future__ import annotations

from typing import Protocol, runtime_checkable

from coactra.workflow.models import Procedure
from coactra.workflow.scope import Scope


@runtime_checkable
class ProcedureStore(Protocol):
    def save(self, procedure: Procedure, scope: Scope) -> None:
        """Persist (or overwrite) a procedure by name within scope."""
        ...

    def get(self, name: str, scope: Scope) -> Procedure | None:
        """Fetch a procedure by name within scope, or None."""
        ...

    def list(self, scope: Scope) -> list[Procedure]:
        """List all procedures in scope."""
        ...


class InMemoryProcedureStore:
    """In-memory, tenant-isolated procedure library (the default ProcedureStore)."""

    def __init__(self) -> None:
        self._store: dict[str, dict[str, Procedure]] = {}

    def _bucket(self, scope: Scope) -> dict[str, Procedure]:
        return self._store.setdefault(scope.key, {})

    def save(self, procedure: Procedure, scope: Scope) -> None:
        self._bucket(scope)[procedure.name] = procedure

    def get(self, name: str, scope: Scope) -> Procedure | None:
        return self._bucket(scope).get(name)

    def list(self, scope: Scope) -> list[Procedure]:
        return list(self._bucket(scope).values())
```

```python
# src/coactra/workflow/__init__.py  (full file — extend imports + __all__)
from coactra.workflow.engine import RunContext, WorkflowEngine
from coactra.workflow.handlers import (
    Approver,
    AutoApprove,
    Collaborator,
    Escalation,
    EscalationRouter,
    EscalationUnresolved,
    NullCollaborator,
    RejectAll,
    TerminalHumanRouter,
)
from coactra.workflow.induction import ReasoningTrace, induce, update
from coactra.workflow.langgraph_engine import LangGraphEngine
from coactra.workflow.models import Procedure, RunResult, Step
from coactra.workflow.scope import Scope
from coactra.workflow.store import InMemoryProcedureStore, ProcedureStore

__version__ = "0.1.0"

__all__ = [
    "__version__",
    "Scope",
    "Step",
    "Procedure",
    "RunResult",
    "RunContext",
    "WorkflowEngine",
    "LangGraphEngine",
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
]
```

- [ ] **Step 4: Run test to verify it passes**

Run: `pytest tests/test_store.py -v`
Expected: PASS (6 passed)

- [ ] **Step 5: Commit**

```bash
git add src/coactra/workflow/store.py src/coactra/workflow/__init__.py tests/test_store.py
git commit -m "feat(workflow): InMemoryProcedureStore — tenant-scoped save/get/list reuse"
```

---

## Task 10: Optional-extra engine stubs (Temporal / Prefect, raise on use)

**Files:**
- Create: `src/coactra/workflow/adapters/__init__.py`
- Create: `src/coactra/workflow/adapters/_stub.py`
- Create: `src/coactra/workflow/adapters/temporal.py`
- Create: `src/coactra/workflow/adapters/prefect.py`
- Test: `tests/test_adapter_stubs.py`

- [ ] **Step 1: Write the failing test**

```python
# tests/test_adapter_stubs.py
import pytest

from coactra.workflow.adapters._stub import MissingExtraError
from coactra.workflow.adapters.prefect import PrefectEngine
from coactra.workflow.adapters.temporal import TemporalEngine


@pytest.mark.parametrize("cls,extra", [
    (TemporalEngine, "temporal"),
    (PrefectEngine, "prefect"),
])
def test_stub_instantiation_raises_until_extra_and_impl_land(cls, extra):
    with pytest.raises(MissingExtraError, match=extra):
        cls()


def test_stubs_name_the_engine_seam_they_will_satisfy():
    assert TemporalEngine.satisfies == "WorkflowEngine"
    assert PrefectEngine.satisfies == "WorkflowEngine"
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/test_adapter_stubs.py -v`
Expected: FAIL with `ModuleNotFoundError: No module named 'coactra.workflow.adapters'`

- [ ] **Step 3: Write minimal implementation**

```python
# src/coactra/workflow/adapters/__init__.py
"""Optional-extra engine adapters. Stubs today — each names the WorkflowEngine seam it
will satisfy and raises MissingExtraError until its extra (and a real impl) land."""
```

```python
# src/coactra/workflow/adapters/_stub.py
"""Shared helper for optional-extra engine stubs."""

from __future__ import annotations


class MissingExtraError(RuntimeError):
    """Raised when an optional-extra engine is used before its extra/impl exist."""


def require_extra(extra: str) -> None:
    raise MissingExtraError(
        f"engine requires the optional '{extra}' extra and a real implementation; "
        f"install with: pip install coactra-workflow[{extra}] (stub not yet implemented)"
    )
```

```python
# src/coactra/workflow/adapters/temporal.py
"""Temporal adapter — STUB. Will satisfy WorkflowEngine; raises until the temporal extra."""

from __future__ import annotations

from coactra.workflow.adapters._stub import require_extra


class TemporalEngine:
    satisfies = "WorkflowEngine"

    def __init__(self, *args, **kwargs) -> None:
        require_extra("temporal")
```

```python
# src/coactra/workflow/adapters/prefect.py
"""Prefect adapter — STUB. Will satisfy WorkflowEngine; raises until the prefect extra."""

from __future__ import annotations

from coactra.workflow.adapters._stub import require_extra


class PrefectEngine:
    satisfies = "WorkflowEngine"

    def __init__(self, *args, **kwargs) -> None:
        require_extra("prefect")
```

- [ ] **Step 4: Run test to verify it passes**

Run: `pytest tests/test_adapter_stubs.py -v`
Expected: PASS (3 passed)

- [ ] **Step 5: Commit**

```bash
git add src/coactra/workflow/adapters tests/test_adapter_stubs.py
git commit -m "feat(workflow): Temporal/Prefect engine stubs (name the seam, raise on use)"
```

---

## Task 11: Full-suite green + public API lock

**Files:**
- Test: `tests/test_public_api.py`

- [ ] **Step 1: Write the failing test**

```python
# tests/test_public_api.py
import coactra.workflow as w


def test_public_surface_is_complete():
    expected = {
        "__version__",
        "Scope",
        "Step",
        "Procedure",
        "RunResult",
        "RunContext",
        "WorkflowEngine",
        "LangGraphEngine",
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
        steps=[w.Step(id="build", kind="task", next="verify"), w.Step(id="verify", kind="task")],
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
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/test_public_api.py -v`
Expected: FAIL only if any `__all__` entry is missing; otherwise it confirms the surface assembled across Tasks 1-10.

- [ ] **Step 3: No new implementation**

The public API was assembled incrementally. This task adds the surface-lock + end-to-end test only. If `test_public_surface_is_complete` fails, add the missing names to `__init__.py` `__all__` (do not weaken the test).

- [ ] **Step 4: Run the full suite**

Run: `pytest -v`
Expected: PASS (all tests across all files green)

- [ ] **Step 5: Commit**

```bash
git add tests/test_public_api.py
git commit -m "test(workflow): lock public API surface + end-to-end author/run/store/induce"
```

---

## Self-Review Checklist (run after implementing)

1. **Charter coverage** — procedure-as-data with one shape for authored + induced (Task 3 + Task 8 keystone); AWM-style `induce()` + manual `update()` (Task 8); collaboration (`ask`) + escalation (`escalate`) as first-class steps routed through injected handlers (Tasks 4/7); reuse via a tenant-scoped store (Task 9). ✔
2. **Open research risk answered** — "is online learned control-flow bolt-on-able or fork-forcing?" → bolt-on-able, proven by the keystone test: an induced Procedure runs the *same* `LangGraphEngine.compile()→run()` path as an authored one with identical results (Task 8). ✔
3. **THIN over LangGraph** — control flow delegated to LangGraph natives (nodes + `add_conditional_edges` + `.compile()`/`.invoke()`); conformance test asserts the artifact is a real `CompiledStateGraph` and branches use native conditional edges (Task 6). No re-implemented interpreter. ✔
4. **Principles** — `WorkflowEngine` Protocol + ONE working default (LangGraph) + Temporal/Prefect stubs (Tasks 5/6/10); `Scope` on every run + isolation proven (Tasks 2/9); honest induction (no auto-relearn, `test_does_not_overclaim_learning_update_is_manual`). ✔
5. **Boundary discipline** — workflow owns when/what; `organization` routes who (injected `EscalationRouter`, `test_workflow_holds_no_org_logic`); `agent` carries talk (injected `Collaborator`); no `coactra.ai` import — `induce()` takes a local `ReasoningTrace` (deps stay langgraph + pydantic). ✔
6. **Packaging** — PEP 420 namespace (no `src/coactra/__init__.py`, Task 1 asserts it), src layout, `py.typed`, hatchling, optional extras `temporal`/`prefect`/`dev`. ✔
7. **Type consistency** — `Scope.key`, `Step(kind=...)`, `Procedure.step()/entry/is_induced`, `RunResult.path/output`, `RunContext(scope/approver/collaborator/router/chain)`, `WorkflowEngine.run`, `LangGraphEngine.compile/run`, `ReasoningTrace.problem/steps`, `induce`/`update`, `ProcedureStore.save/get/list` used identically across tasks. ✔
