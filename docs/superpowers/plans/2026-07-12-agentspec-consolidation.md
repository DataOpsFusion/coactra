# AgentSpec Consolidation Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Replace the four duplicate agent-description types (`_AgentSpec`, `TeamAgentSpec`, and the 17-kwarg signatures of `Team.add_agent()` / `build_agent()`) with one public, frozen `coactra.AgentSpec` that carries identity, scope, model routing, skills, tools, memory, and policy-relevant config through the whole construction path.

**Architecture:** `AgentSpec` is a frozen dataclass in `coactra/src/coactra/agent/spec.py`. `Team.add_agent()` accepts a spec (or keyword sugar that builds one), resolves the model route, stamps the team `Scope` (with `agent_id`) onto a resolved copy via `dataclasses.replace`, and hands that single object to `build_agent(spec, policy=...)`. `Team` stays a convenience facade; the spec is the canonical construction contract. Private cross-module reach-ins (`agent._name`, `agent._skills`, `model_resolver._routes`) are replaced with public properties.

**Tech Stack:** Python 3.12+, dataclasses, pydantic v2 (core dep), pydantic-ai (test/runtime extra), pytest with `asyncio_mode = "auto"`, ruff, pyright (basic).

## Global Constraints

- All commands run from `/Users/datta/Documents/Projects/coactra/coactra` (the inner package dir that holds `pyproject.toml`). Use the project venv: `.venv/bin/python -m pytest`, `.venv/bin/ruff`. If `.venv` is missing, create it: `python3 -m venv .venv && .venv/bin/pip install -e '.[all,dev]'`.
- Core import rule: `coactra/src/coactra/agent/spec.py` may import only stdlib, `coactra.scope`, and `coactra.agent.skills`. It must NOT import `pydantic_ai` (directly or transitively) at module import time.
- No new dependencies. No changes to `pyproject.toml`.
- Line length 100 (ruff). Run `.venv/bin/ruff check src tests` before every commit; it must be clean.
- The repo currently has uncommitted work-in-progress (a workflow-API trim touching `agent/workflow.py`, `workflow/__init__.py`, docs, and a new `agent/recipes.py`). **That WIP must be committed by Dave before this plan starts.** Never mix those files into this plan's commits. If the tree is dirty with unrelated changes at start, stop and ask.
- Existing behavior of `Team.add_agent(name=..., ...)` keyword call sites (37 in tests, 1 in `src/coactra/cli.py`) must keep working unchanged — the keyword form becomes sugar over `AgentSpec`.
- The full suite (`.venv/bin/python -m pytest`) must be green at the end of every task. Baseline is ~559 tests passing, `live`-marked tests excluded by default (already configured in `pyproject.toml`).
- Error-message compatibility: keep the existing `add_agent` no-capability `TypeError` text and the `build_agent` unknown-defaults `TypeError` text exactly as they are today (some tests may match on them; verify with grep before changing any message).

## Out of Scope (do not do these in this plan)

- Unifying the per-package `Scope` classes in `memory`, `workspace`, `workflow` (next milestone).
- Removing or moving `coactra/agent/recipes.py` (belongs to the in-flight workflow trim).
- Any adapter/extras reorganization, Hermes integration, or deprecation of `Team`.

---

### Task 0: Verify green baseline

**Files:** none modified.

- [ ] **Step 1: Confirm the working tree is clean**

Run: `git status --porcelain`
Expected: empty output. If not empty, STOP — the pre-existing WIP must be committed first (by Dave, or as an explicit separate commit approved by Dave). Do not proceed with a dirty tree.

- [ ] **Step 2: Run the full suite**

Run: `cd /Users/datta/Documents/Projects/coactra/coactra && .venv/bin/python -m pytest -q`
Expected: all tests pass (0 failures). Record the passing count; it is the baseline for every later task.

- [ ] **Step 3: Run lint baseline**

Run: `.venv/bin/ruff check src tests`
Expected: no errors.

---

### Task 1: Public `AgentSpec` dataclass

**Files:**
- Create: `coactra/src/coactra/agent/spec.py`
- Create: `coactra/tests/agent/test_spec.py`
- Modify: `coactra/src/coactra/agent/__init__.py` (add lazy export)
- Modify: `coactra/src/coactra/__init__.py` (add top-level lazy export)

**Interfaces:**
- Consumes: `Skill`, `normalize_skills` from `coactra.agent.skills`; `Scope` from `coactra.scope` (the canonical DTO — NOT `coactra.agent.domain.Scope`, which is a different class).
- Produces: `AgentSpec` — frozen dataclass with fields `name: str`, `model: Any | None`, `model_capability: str | None`, `instructions: str | None`, `scope: Scope | None`, `tools: tuple[Any, ...]`, `skills` (normalized to `tuple[Skill, ...]`), `memory: Any`, `workspace: Any`, `runtime: Any | None`, `api_base: str | None`, `api_key: str | None`, `gateway: str | None`, `auth: Any`, `expose: bool`, `peers: tuple[Any, ...]`, `registry: Any | None`, `tracer: Any | None`, `defaults: Mapping[str, Any]`. Tasks 3–5 rely on these exact names (they mirror today's `_AgentSpec` in `team/facade.py:36`).

- [ ] **Step 1: Write the failing tests**

Create `coactra/tests/agent/test_spec.py`:

```python
from __future__ import annotations

import dataclasses

import pytest

from coactra import AgentSpec, Scope
from coactra.agent.skills import Skill


def test_agent_spec_minimal_defaults():
    spec = AgentSpec(name="helper")
    assert spec.name == "helper"
    assert spec.model is None
    assert spec.model_capability is None
    assert spec.instructions is None
    assert spec.scope is None
    assert spec.tools == ()
    assert spec.skills == ()
    assert spec.peers == ()
    assert spec.defaults == {}
    assert spec.expose is False
    assert spec.runtime is None


def test_agent_spec_requires_non_empty_name():
    with pytest.raises(ValueError):
        AgentSpec(name="")


def test_agent_spec_normalizes_sequences_and_skills():
    spec = AgentSpec(
        name="helper",
        tools=[print],
        peers=["other"],
        skills=[Skill("python", tags=("implement",)), {"id": "review"}],
        defaults={"gateway": "openai"},
    )
    assert isinstance(spec.tools, tuple)
    assert isinstance(spec.peers, tuple)
    assert [skill.id for skill in spec.skills] == ["python", "review"]
    assert all(isinstance(skill, Skill) for skill in spec.skills)
    assert spec.defaults == {"gateway": "openai"}


def test_agent_spec_accepts_string_skill_shorthand():
    spec = AgentSpec(name="helper", skills="rotate certs")
    assert len(spec.skills) == 1
    assert spec.skills[0].id == "general"


def test_agent_spec_is_frozen_and_replaceable():
    spec = AgentSpec(name="helper")
    with pytest.raises(dataclasses.FrozenInstanceError):
        spec.name = "other"  # type: ignore[misc]
    resolved = dataclasses.replace(
        spec, scope=Scope(tenant_id="acme", agent_id="helper")
    )
    assert resolved.scope is not None
    assert resolved.scope.tenant_id == "acme"
    assert spec.scope is None


def test_agent_spec_is_a_lazy_top_level_export():
    import coactra

    assert "AgentSpec" in coactra.__all__
    assert coactra.AgentSpec is AgentSpec
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `.venv/bin/python -m pytest tests/agent/test_spec.py -v`
Expected: FAIL — `ImportError: cannot import name 'AgentSpec' from 'coactra'`.

- [ ] **Step 3: Implement `AgentSpec`**

Create `coactra/src/coactra/agent/spec.py`:

```python
"""AgentSpec — the canonical declarative description of one agent.

One object carries identity, model routing, scope, skills, tools, memory,
and runtime configuration through the whole construction path
(``Team.add_agent`` -> ``build_agent``). Frozen: model resolution produces
a new copy via ``dataclasses.replace`` instead of mutating.
"""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass, field
from typing import Any

from coactra.agent.skills import normalize_skills
from coactra.scope import Scope

__all__ = ["AgentSpec"]


@dataclass(frozen=True, slots=True)
class AgentSpec:
    """Declarative composition of one agent.

    ``skills`` accepts anything :func:`coactra.agent.skills.normalize_skills`
    accepts (str, Skill, dict, or a sequence of those) and is normalized to
    ``tuple[Skill, ...]`` on construction. ``defaults`` are extra runtime
    keyword arguments forwarded to the runtime adapter. ``scope`` is filled
    in by :class:`coactra.Team` when left as None.
    """

    name: str
    model: Any | None = None
    model_capability: str | None = None
    instructions: str | None = None
    scope: Scope | None = None
    tools: tuple[Any, ...] = ()
    skills: Any = ()
    memory: Any = None
    workspace: Any = None
    runtime: Any | None = None
    api_base: str | None = None
    api_key: str | None = None
    gateway: str | None = None
    auth: Any = None
    expose: bool = False
    peers: tuple[Any, ...] = ()
    registry: Any | None = None
    tracer: Any | None = None
    defaults: Mapping[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        if not isinstance(self.name, str) or not self.name:
            raise ValueError("AgentSpec.name must be a non-empty string")
        object.__setattr__(self, "tools", tuple(self.tools))
        object.__setattr__(self, "peers", tuple(self.peers))
        raw_skills = self.skills
        if isinstance(raw_skills, tuple):
            raw_skills = list(raw_skills)
        object.__setattr__(self, "skills", tuple(normalize_skills(raw_skills)))
        object.__setattr__(self, "defaults", dict(self.defaults))
```

Note: `normalize_skills` is typed `None | str | Skill | list[Skill | dict]`; the tuple→list conversion above is what makes tuple inputs (including the `()` default) valid. The docstring's `Skill` references don't need an import (`skills` is typed `Any` because it accepts pre-normalization shapes).

- [ ] **Step 4: Wire the lazy exports**

In `coactra/src/coactra/agent/__init__.py`, add one entry to the `_LAZY_EXPORTS` dict (keep alphabetical position next to `"Agent"`):

```python
    "AgentSpec": ("coactra.agent.spec", "AgentSpec"),
```

and add `"AgentSpec"` to that module's `__all__` list (it starts right after the `_LAZY_EXPORTS` dict; read the file to find it).

In `coactra/src/coactra/__init__.py`:
- add `"AgentSpec",` to `__all__` (after `"Agent",`)
- change `_SDK_EXPORTS = frozenset({"Agent", "RemotePeer", "Run"})` to `_SDK_EXPORTS = frozenset({"Agent", "AgentSpec", "RemotePeer", "Run"})`

The existing `__getattr__` fallback already routes `_SDK_EXPORTS` through `coactra.agent`, so no other change is needed.

- [ ] **Step 5: Run tests to verify they pass**

Run: `.venv/bin/python -m pytest tests/agent/test_spec.py tests/agent/test_toplevel.py tests/arch/ -v`
Expected: PASS. If `tests/agent/test_toplevel.py` asserts an exact export list, add `AgentSpec` to its expected names — read the failure message and update the test's expectation, nothing else.

- [ ] **Step 6: Lint and commit**

Run: `.venv/bin/ruff check src tests`
Expected: clean.

```bash
git add src/coactra/agent/spec.py tests/agent/test_spec.py src/coactra/agent/__init__.py src/coactra/__init__.py tests/agent/test_toplevel.py
git commit -m "feat: add public AgentSpec as the canonical agent composition object"
```

---

### Task 2: Public surface for `Agent` and `ModelResolver` (kill the reach-ins)

**Files:**
- Modify: `coactra/src/coactra/agent/facade.py:35-103` (the `Agent` class)
- Modify: `coactra/src/coactra/model/resolver.py:14-27`
- Create: `coactra/tests/agent/test_agent_surface.py`

**Interfaces:**
- Produces: `Agent.name -> str`, `Agent.tenant -> str`, `Agent.skills -> tuple[Skill, ...]`, `Agent.add_skill(skill: Skill) -> Skill`, `ModelResolver.capabilities -> tuple[str, ...]`. Task 4 replaces `Team`'s `agent._name` / `agent._skills` / `resolver._routes` accesses with these.

- [ ] **Step 1: Write the failing tests**

Create `coactra/tests/agent/test_agent_surface.py`:

```python
from __future__ import annotations

from coactra.agent.facade import Agent
from coactra.agent.skills import Skill
from coactra.model import ModelProfile, ModelResolver, ModelRoute


class _NullRuntime:
    async def run(self, prompt, *, run_id, output_type=None, message_history=None):
        raise NotImplementedError

    def stream(
        self, prompt, *, run_id, output_type=None, message_history=None, on_result=None
    ):
        raise NotImplementedError


def test_agent_exposes_name_tenant_and_skills():
    agent = Agent(_NullRuntime(), name="helper", tenant="acme", skills=[Skill("python")])
    assert agent.name == "helper"
    assert agent.tenant == "acme"
    assert [skill.id for skill in agent.skills] == ["python"]
    assert isinstance(agent.skills, tuple)


def test_agent_add_skill_deduplicates_by_id():
    agent = Agent(_NullRuntime(), name="helper")
    agent.add_skill(Skill("python"))
    agent.add_skill(Skill("python"))
    assert len(agent.skills) == 1


def test_model_resolver_exposes_capabilities():
    resolver = ModelResolver(
        [ModelRoute(capability="default", profile=ModelProfile(name="default", model="test"))]
    )
    assert resolver.capabilities == ("default",)
```

(If `ModelProfile` requires more constructor arguments than `name` and `model`, mirror the construction used in `Team.local` at `src/coactra/team/facade.py:96-105`.)

- [ ] **Step 2: Run tests to verify they fail**

Run: `.venv/bin/python -m pytest tests/agent/test_agent_surface.py -v`
Expected: FAIL — `AttributeError: 'Agent' object has no attribute 'name'` (and similar).

- [ ] **Step 3: Implement the properties**

In `coactra/src/coactra/agent/facade.py`, inside `class Agent`, directly above the existing `card` property, add:

```python
    @property
    def name(self) -> str:
        return self._name

    @property
    def tenant(self) -> str:
        return self._tenant

    @property
    def skills(self) -> tuple[Skill, ...]:
        return tuple(self._skills)

    def add_skill(self, skill: Skill) -> Skill:
        """Attach a skill unless one with the same id is already present."""
        if not any(existing.id == skill.id for existing in self._skills):
            self._skills.append(skill)
        return skill
```

In `coactra/src/coactra/model/resolver.py`, inside `class ModelResolver`, after `register`, add:

```python
    @property
    def capabilities(self) -> tuple[str, ...]:
        """Registered capability names, in registration order."""
        return tuple(self._routes)
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `.venv/bin/python -m pytest tests/agent/test_agent_surface.py tests/model/ tests/agent/test_facade.py -v`
Expected: PASS.

- [ ] **Step 5: Lint and commit**

```bash
.venv/bin/ruff check src tests
git add src/coactra/agent/facade.py src/coactra/model/resolver.py tests/agent/test_agent_surface.py
git commit -m "feat: public name/tenant/skills/add_skill on Agent, capabilities on ModelResolver"
```

---

### Task 3: `build_agent` consumes an `AgentSpec`

**Files:**
- Modify: `coactra/src/coactra/agent/facade.py:106-168` (`build_agent`)
- Modify: `coactra/src/coactra/team/facade.py:218-240` (the sole caller)
- Test: `coactra/tests/agent/test_agent_surface.py` (append one test)

**Interfaces:**
- Consumes: `AgentSpec` from Task 1 (`from coactra.agent.spec import AgentSpec`).
- Produces: `async def build_agent(spec: AgentSpec, *, policy: Any | None = None) -> Agent`. Task 4 calls exactly this. Tenant is derived from `spec.scope.tenant_id` when `spec.scope` is set, else `None` (the `Agent` constructor already defaults tenant to `"default"`).

- [ ] **Step 1: Write the failing test**

Append to `coactra/tests/agent/test_agent_surface.py`:

```python
async def test_build_agent_from_spec_with_custom_runtime():
    from coactra import AgentSpec, Scope
    from coactra.agent.facade import build_agent

    spec = AgentSpec(
        name="helper",
        runtime=_NullRuntime(),
        skills="review things",
        scope=Scope(tenant_id="acme", agent_id="helper"),
        expose=True,
    )
    agent = await build_agent(spec)
    assert agent.name == "helper"
    assert agent.tenant == "acme"
    assert agent.skills[0].id == "general"
    assert agent.card is not None
```

(`asyncio_mode = "auto"` is set in pyproject, so no marker is needed.)

- [ ] **Step 2: Run test to verify it fails**

Run: `.venv/bin/python -m pytest tests/agent/test_agent_surface.py -v`
Expected: FAIL — `TypeError: build_agent() got an unexpected keyword argument` or missing-positional error, because `build_agent` still takes only keywords.

- [ ] **Step 3: Rewrite `build_agent`**

Replace the whole `build_agent` function in `coactra/src/coactra/agent/facade.py` (currently lines 106-168) with:

```python
async def build_agent(spec: AgentSpec, *, policy: Any | None = None) -> Agent:
    """Assemble an Agent from a resolved :class:`coactra.AgentSpec`."""
    unknown = set(spec.defaults) - _KNOWN_RUNTIME_KWARGS
    if unknown:
        raise TypeError(f"build_agent() got unexpected keyword argument(s): {sorted(unknown)}")
    tenant = spec.scope.tenant_id if spec.scope is not None else None
    if spec.runtime is not None:
        return Agent(
            spec.runtime,
            name=spec.name,
            tenant=tenant,
            skills=list(spec.skills),
            expose=spec.expose,
        )

    bindings = build_agent_bindings(
        tools=list(spec.tools),
        skills=list(spec.skills),
        peers=list(spec.peers),
        registry=spec.registry,
        name=spec.name,
        tenant=tenant,
        policy=policy,
    )
    rt = PydanticAIRuntime(
        model=spec.model,
        instructions=spec.instructions,
        tools=bindings.tools,
        api_base=spec.api_base,
        api_key=spec.api_key,
        gateway=spec.gateway,
        auth=spec.auth,
        name=spec.name,
        tenant=tenant,
        memory=spec.memory,
        workspace=spec.workspace,
        tracer=spec.tracer,
        mcp_servers=bindings.mcp_servers,
        **dict(spec.defaults),
    )
    return Agent(
        rt,
        name=spec.name,
        tenant=tenant,
        skills=bindings.skills,
        expose=spec.expose,
        tools=bindings.tools,
    )
```

Add the import at the top of the file with the other `coactra.agent` imports:

```python
from coactra.agent.spec import AgentSpec
```

If `normalize_agent_skills` (from `coactra.agent.bindings`) is now unused in this file, remove it from the import — ruff will flag it.

- [ ] **Step 4: Update the sole caller in `Team.add_agent`**

In `coactra/src/coactra/team/facade.py`, replace the `build_agent(...)` call block (currently lines 218-240, from `from coactra.agent.facade import build_agent` through the closing paren) with a spec-based call. This is an interim bridge — Task 4 restructures the whole method:

```python
        from coactra.agent.facade import build_agent
        from coactra.agent.spec import AgentSpec

        agent = await build_agent(
            AgentSpec(
                name=name,
                model=resolved_model,
                model_capability=effective_model_capability,
                instructions=instructions,
                scope=replace(self.scope, agent_id=name),
                tools=tuple(tools or []),
                skills=tuple(normalized_skills),
                memory=memory,
                workspace=workspace,
                runtime=runtime,
                api_base=effective_api_base,
                api_key=effective_api_key,
                gateway=gateway,
                auth=auth,
                expose=expose,
                peers=tuple(peers or []),
                registry=registry,
                tracer=tracer,
                defaults=effective_defaults,
            ),
            policy=self.policy,
        )
```

Add `replace` to the dataclasses import at the top of `team/facade.py`:

```python
from dataclasses import dataclass, field, replace
```

Note the behavior delta this bridge introduces on purpose: the agent's scope now carries `agent_id=name` and `Agent.tenant` comes from that scope — same tenant value as before (`self.scope.tenant_id`), so nothing observable changes.

- [ ] **Step 5: Run the affected suites**

Run: `.venv/bin/python -m pytest tests/agent/ tests/team/ tests/model/ -v`
Expected: PASS (all).

- [ ] **Step 6: Lint and commit**

```bash
.venv/bin/ruff check src tests
git add src/coactra/agent/facade.py src/coactra/team/facade.py tests/agent/test_agent_surface.py
git commit -m "refactor: build_agent consumes AgentSpec instead of 17 keyword args"
```

---

### Task 4: `Team.add_agent` — one canonical spec path, delete `_AgentSpec`

**Files:**
- Modify: `coactra/src/coactra/team/facade.py` (delete `_AgentSpec` at lines 35-54; rewrite `add_agent` at 148-242; update `_has_required_tags`, `__init__`, `assign_skill`, `match_skills`, `match_skill`)
- Modify: `coactra/tests/agent/test_team.py` (append new tests; change `._name` → `.name` at lines 134, 135, 233)

**Interfaces:**
- Consumes: `AgentSpec` (Task 1), `build_agent(spec, *, policy)` (Task 3), `Agent.name/skills/add_skill` and `ModelResolver.capabilities` (Task 2).
- Produces: `async def add_agent(self, spec: AgentSpec | None = None, /, **kwargs: Any) -> Agent` and `def spec(self, name: str) -> AgentSpec | None`. Task 5's `from_spec` calls `add_agent(spec)` directly. Keyword form still works: unknown keywords fold into `defaults` (preserving today's `**defaults` catch-all).

- [ ] **Step 1: Write the failing tests**

Append to `coactra/tests/agent/test_team.py` (it already imports `Team`; add `AgentSpec` and `Scope` to its `from coactra import ...` line, and `pytest` / `TestModel` are already imported there — verify and add if missing):

```python
async def test_add_agent_accepts_agent_spec_directly():
    team = Team.local(model=TestModel(), tenant_id="acme")
    agent = await team.add_agent(AgentSpec(name="helper", skills="review things"))
    assert agent.name == "helper"
    assert team.member("helper") is agent
    resolved = team.spec("helper")
    assert resolved is not None
    assert resolved.scope == Scope(tenant_id="acme", namespace="default", agent_id="helper")


async def test_add_agent_with_explicit_model_needs_no_default_route():
    from coactra.policy import permissive

    team = Team(scope=Scope(tenant_id="acme"), policy=permissive())
    agent = await team.add_agent(AgentSpec(name="helper", model=TestModel()))
    assert agent.name == "helper"
    assert team.spec("helper").model_capability == "agent:helper"


async def test_add_agent_rejects_spec_plus_kwargs():
    team = Team.local(model=TestModel())
    with pytest.raises(TypeError):
        await team.add_agent(AgentSpec(name="helper"), instructions="nope")


async def test_add_agent_rejects_foreign_tenant_scope():
    team = Team.local(model=TestModel(), tenant_id="acme")
    foreign = AgentSpec(name="helper", scope=Scope(tenant_id="other"))
    with pytest.raises(ValueError):
        await team.add_agent(foreign)
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `.venv/bin/python -m pytest tests/agent/test_team.py -v`
Expected: the four new tests FAIL (`add_agent` doesn't accept a positional spec; `Team.spec` doesn't exist). All pre-existing tests still PASS.

- [ ] **Step 3: Restructure `Team`**

In `coactra/src/coactra/team/facade.py`:

3a. Update imports: add `fields` to the dataclasses import (now `from dataclasses import dataclass, field, fields, replace` — then remove `dataclass`/`field` from it if nothing else in the file uses them after 3b) and add a top-level `from coactra.agent.spec import AgentSpec`. Remove `normalize_skills` from the `coactra.agent.skills` import if it becomes unused (keep `Skill`).

3b. Delete the `_AgentSpec` dataclass entirely (lines 35-54).

3c. Change `_has_required_tags` (lines 25-32) to use the public property:

```python
def _has_required_tags(agent: Any, required_tags: tuple[str, ...]) -> bool:
    if not required_tags:
        return True
    required = set(required_tags)
    return any(required <= set(skill.tags) for skill in agent.skills)
```

(If `Skill.tags` can be unset, keep the `getattr(skill, "tags", ())` form inside the comprehension.)

3d. In `__init__`, replace the private reach-in (lines 71-73):

```python
        if default_model_capability is None and model_resolver is not None:
            default_model_capability = next(iter(model_resolver.capabilities), None)
```

and change the specs dict annotation: `self._agent_specs: dict[str, AgentSpec] = {}`.

3e. Replace the whole `add_agent` method (which after Task 3 spans the signature through the `return agent`) with:

```python
    async def add_agent(self, spec: AgentSpec | None = None, /, **kwargs: Any) -> Agent:
        """Register and build an Agent owned by this Team.

        Accepts a prepared :class:`coactra.AgentSpec`, or the same fields as
        keyword arguments. Unknown keywords fold into ``defaults``.
        """
        if spec is not None and kwargs:
            raise TypeError("pass either an AgentSpec or keyword fields, not both")
        if spec is None:
            known = {f.name for f in fields(AgentSpec)}
            extras = {key: kwargs.pop(key) for key in list(kwargs) if key not in known}
            if extras:
                kwargs["defaults"] = {**extras, **dict(kwargs.get("defaults", {}))}
            spec = AgentSpec(**kwargs)
        return await self._register(spec)

    async def _register(self, spec: AgentSpec) -> Agent:
        if spec.name in self._agent_specs:
            raise ValueError(f"agent {spec.name!r} is already registered")
        if spec.scope is not None and spec.scope.tenant_id != self.scope.tenant_id:
            raise ValueError(
                f"agent scope tenant {spec.scope.tenant_id!r} does not match "
                f"team tenant {self.scope.tenant_id!r}"
            )

        capability = spec.model_capability
        if spec.model is not None:
            capability = capability or f"agent:{spec.name}"
            self.add_model(capability, spec.model, api_base=spec.api_base, api_key=spec.api_key)
        else:
            capability = capability or self._default_model_capability
        if capability is None:
            raise TypeError(
                "add_agent() requires model_capability= or a Team default route; "
                "use Team.local(model=...) for the low-ceremony path"
            )
        if self._model_resolver is None:
            raise ValueError("Team has no model_resolver; configure routes before add_agent()")

        route = await self._model_resolver.resolve(
            capability,
            principal=f"agent:{spec.name}",
            scope=self.scope,
            policy=self.policy,
            context={"agent_name": spec.name},
        )
        resolved = replace(
            spec,
            model=route.model,
            model_capability=capability,
            scope=spec.scope or replace(self.scope, agent_id=spec.name),
            api_base=spec.api_base if spec.api_base is not None else route.api_base,
            api_key=spec.api_key if spec.api_key is not None else route.api_key,
            defaults={**route.defaults, **dict(spec.defaults)},
        )
        self._agent_specs[spec.name] = resolved
        for skill in resolved.skills:
            self._skills.setdefault(skill.id, skill)

        from coactra.agent.facade import build_agent

        agent = await build_agent(resolved, policy=self.policy)
        self._agents[spec.name] = agent
        return agent

    def spec(self, name: str) -> AgentSpec | None:
        """Return the resolved AgentSpec registered under ``name``."""
        return self._agent_specs.get(name)
```

3f. Rewrite `assign_skill` (AgentSpec is frozen, so replace instead of append):

```python
    def assign_skill(self, agent_name: str, skill: Skill) -> Skill:
        agent = self.member(agent_name)
        if agent is None:
            raise KeyError(f"unknown agent {agent_name!r}")
        spec = self._agent_specs[agent_name]
        if not any(existing.id == skill.id for existing in spec.skills):
            self._agent_specs[agent_name] = replace(spec, skills=[*spec.skills, skill])
        agent.add_skill(skill)
        self._skills[skill.id] = skill
        return skill
```

3g. In `match_skills`, change `skills = getattr(agent, "_skills", [])` to `skills = agent.skills`. In `match_skill`, change the ambiguity message list comprehension from `[agent._name for agent in matches]` to `[agent.name for agent in matches]`.

3h. In `coactra/tests/agent/test_team.py` lines 134, 135, and 233, change `._name` to `.name`.

- [ ] **Step 4: Run the affected suites**

Run: `.venv/bin/python -m pytest tests/agent/ tests/team/ tests/model/ -q`
Expected: PASS. Also run `tests/test_docs_imports.py` and the cli path: `.venv/bin/python -m pytest tests/ -q -k "cli or docs"` — the keyword sugar must keep `src/coactra/cli.py:50` (`team.add_agent(name="assistant")`) working.

- [ ] **Step 5: Lint and commit**

```bash
.venv/bin/ruff check src tests
git add src/coactra/team/facade.py tests/agent/test_team.py
git commit -m "refactor: Team.add_agent takes AgentSpec (kwargs kept as sugar); delete _AgentSpec"
```

---

### Task 5: `from_spec` uses `AgentSpec`; delete `TeamAgentSpec`

**Files:**
- Modify: `coactra/src/coactra/team/facade.py:370-433` (`from_spec`)
- Delete: `coactra/src/coactra/team/spec.py`
- Modify: `coactra/tests/team/test_spec.py`

**Interfaces:**
- Consumes: `add_agent(spec)` from Task 4 (its explicit-model branch replaces `from_spec`'s manual `add_model` dance).
- Produces: `Team.from_spec(*, model, agents: Sequence[AgentSpec], ...)` — same keyword signature as today except `agents` takes `AgentSpec` items.

- [ ] **Step 1: Update the test to the new API (it becomes the failing test)**

Rewrite `coactra/tests/team/test_spec.py`:

```python
from __future__ import annotations

import pytest
from pydantic_ai.models.test import TestModel

from coactra import AgentSpec, Scope, Team
from coactra.agent.skills import Skill


@pytest.mark.asyncio
async def test_team_from_spec_builds_agents_and_routes_skills():
    team = await Team.from_spec(
        model=TestModel(),
        tenant_id="acme",
        namespace="spec",
        agents=[
            AgentSpec("builder", skills=(Skill("python", tags=("implement",)),), expose=True),
            AgentSpec("reviewer", skills=(Skill("python", tags=("review",)),), expose=True),
        ],
    )

    assert team.scope == Scope(tenant_id="acme", namespace="spec")
    assert team.member("builder") is not None
    assert team.match_skill("python", required_tags=["review"]).name == "reviewer"
```

Preserve any other tests already in this file by porting them the same way: `TeamAgentSpec(...)` → `AgentSpec(...)` (field names are identical), `._name` → `.name`.

- [ ] **Step 2: Run test to verify current state**

Run: `.venv/bin/python -m pytest tests/team/test_spec.py -v`
Expected: PASS already (both forms currently coexist) or FAIL only on the import if `TeamAgentSpec` was the only import — either way, proceed; the deletion in Step 3 is what this test guards.

- [ ] **Step 3: Rewrite `from_spec` and delete the old spec module**

In `coactra/src/coactra/team/facade.py`, replace the `for spec in agents:` loop body (currently lines 403-432, the `add_model` special-casing plus the 15-keyword `add_agent` call) with:

```python
        for spec in agents:
            await team.add_agent(spec)
```

Change the signature's `agents: list[TeamAgentSpec] | tuple[TeamAgentSpec, ...]` to `agents: Sequence[AgentSpec]` and add `from collections.abc import Sequence` to the imports. Remove the `from coactra.team.spec import TeamAgentSpec` import.

Then delete the file:

```bash
git rm src/coactra/team/spec.py
```

Verify nothing else references it:

Run: `grep -rn "TeamAgentSpec\|team\.spec\|team/spec" src tests ../docs`
Expected: no matches (except possibly this plan document).

Behavior note (intentional, covered by Task 4's explicit-model branch): `from_spec` used to register per-agent routes with the spec's `defaults` baked into the `ModelProfile`; now the route registers without them and `_register` merges `spec.defaults` at resolution time. The effective runtime defaults are identical; only resolver introspection of the profile differs.

- [ ] **Step 4: Run the affected suites**

Run: `.venv/bin/python -m pytest tests/team/ tests/agent/ -q`
Expected: PASS.

- [ ] **Step 5: Lint and commit**

```bash
.venv/bin/ruff check src tests
git add -A src/coactra/team tests/team/test_spec.py
git commit -m "refactor: from_spec takes AgentSpec; delete TeamAgentSpec"
```

---

### Task 6: Docs, type-check, full verification

**Files:**
- Modify: `docs/API_INDEX.md` (repo root `docs/`, not inside `coactra/`)

- [ ] **Step 1: Document `AgentSpec`**

In `docs/API_INDEX.md`:
- Add `AgentSpec,` to the root-import listing at lines 9-12 (keep alphabetical: right after `Agent,`).
- Add a table row after the `Agent` row (line 18):

```markdown
| `AgentSpec` | dataclass | **Available** | Canonical declarative composition of one agent: identity, model routing, scope, skills, tools, memory, runtime config. |
```

- In the `## Team.add_agent(...)` section (line 68), after the existing keyword example, add:

````markdown
The same construction as an explicit spec — `AgentSpec` is the canonical form; the
keyword arguments above are convenience sugar over it:

```python
from coactra import AgentSpec

agent = await team.add_agent(
    AgentSpec(
        name="security-agent",
        model_capability="reasoning",
        instructions="You handle certificate rotation.",
        skills=[Skill(id="security", description="...", tags=["review", "tls"])],
    )
)
```
````

- [ ] **Step 2: Run the docs-import guard**

Run: `.venv/bin/python -m pytest tests/test_docs_imports.py -v`
Expected: PASS (this test resolves every symbol documented in the docs; it proves the new docs entries import cleanly).

- [ ] **Step 3: Full verification**

Run each; all must be clean:

```bash
.venv/bin/python -m pytest -q
.venv/bin/ruff check src tests
.venv/bin/pyright
```

Expected: test count ≥ baseline from Task 0 plus the ~12 new tests, 0 failures; ruff clean; pyright no new errors (its include list already covers `src/coactra/agent` and `src/coactra/team/facade.py`).

- [ ] **Step 4: Commit**

```bash
git add ../docs/API_INDEX.md
git commit -m "docs: document AgentSpec as the canonical construction path"
```
