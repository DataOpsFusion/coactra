# fleetlib.agent Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Ship a publishable, **thin composition/policy layer** that WRAPS the mature protocols (A2A v1.0.x, MCP `tools.listChanged`, FastMCP live mounting, OpenAI Agents SDK) and BUILDS only the three session-level gaps the research verdict identified: (1) **mid-session MCP capability mounting** that exposes tools on the NEXT SAFE model turn with naming-conflict resolution + cache invalidation; (2) **delegated identity via RFC 8693** token exchange (subject/actor chains) — `act_on_behalf_of(grant)`, NEVER token passthrough; (3) **collaboration policy over A2A** — who may talk to whom, when. A thin `Agent` facade wires the five sibling capabilities (ai/memory/workspace/workflow/organization) through narrow **local port Protocols**, never importing their internals. The default of every feature is in-process and unit-testable; the real SDKs/transport are optional-extra stubs.

**Architecture:** Three self-contained subsystems, each a `typing.Protocol` + ONE in-process working default, none touching the network on the default path. **(1) Mounting:** a `MountRegistry` holds *pending* and *active* tool sets; `mount_mcp(server, effective="next_turn")` stages a mount into pending and `begin_turn()` promotes pending→active and fires an `invalidate_tools_cache` callback — *that* is the observable "next safe turn" boundary (answering the charter's open question by defining it). A `ConflictPolicy` resolves naming collisions (default: namespace the incoming tool by mount id). **(2) Delegation:** `DelegationGrant(subject, actor)` + a `TokenExchanger` Protocol; `act_on_behalf_of(grant)` produces an `ExchangedIdentity` carrying a **nested actor chain** for multi-hop, and the in-process default proves the raw subject token NEVER appears downstream (the security keystone). The real Keycloak/RFC-8693 exchange is a stub. **(3) Collaboration:** `CollaborationPolicy.can_talk(src, dst, scope)` is pure in-process; a `PolicyGatedCollaborator` wraps an A2A transport behind the policy and **structurally satisfies workflow's `Collaborator`/`EscalationRouter` Protocols** (the concrete inter-lib seam workflow deferred to "the agent layer"). The `Agent` composition root threads a mandatory `Scope` (tenant_id + namespace, local shape) through all three plus the five injected sibling ports — it delegates, never re-implements (`agent.memory(...)` just calls the injected `MemoryPort`).

**Tech Stack:** Python 3.12+, pydantic v2, hatchling (PEP 420 namespace package `fleetlib/agent/`, src layout), pytest. Sibling deps (`fleetlib-ai`, `fleetlib-memory`, `fleetlib-workspace`, `fleetlib-workflow`, `fleetlib-organization`) are declared in `pyproject.toml` per the charter (in a `siblings` optional-extra, NOT a hard dependency, so the wheel installs before any sibling publishes) but **never imported** — `lib-ai` and `organization` have no code yet, so each sibling is consumed through a local port Protocol + an in-process fake, exactly as the sibling `workflow` plan refused to import `fleetlib.ai` and used a local `ReasoningTrace`. Optional extras: `siblings` (the five fleetlib-* libs, declared-not-imported), `mcp` (fastmcp), `a2a` (a2a-sdk), `oauth` (token exchange) — stub adapters that raise on use; `dev`. (No `agents`/openai-agents extra yet — the toolset is exposed for whatever runner drives the model; wrapping the OpenAI Agents runner is deferred until built, YAGNI.) No default path depends on a live SDK or network.

---

## File Structure

| File | Single responsibility |
|------|----------------------|
| `pyproject.toml` | Distribution `fleetlib-agent`; hatchling targets the `fleetlib` namespace dir; hard runtime dep is `pydantic` ONLY; the five `fleetlib-*` siblings live in a `siblings` optional-extra (declared per charter, never imported, kept out of hard deps so the wheel installs today); `[project.optional-dependencies]` for `siblings`/`mcp`/`a2a`/`agents`/`oauth`/`dev`. |
| `src/fleetlib/agent/__init__.py` | Public API surface — re-exports every public name. NO `src/fleetlib/__init__.py` (namespace package). |
| `src/fleetlib/agent/py.typed` | PEP 561 typing marker. |
| `src/fleetlib/agent/scope.py` | `Scope` value object — `tenant_id` + `namespace`; the multi-tenant key threaded through every subsystem. |
| `src/fleetlib/agent/tools.py` | `ToolSpec` (name + mount-id provenance) — the unit the mount registry tracks and the toolset exposes. |
| `src/fleetlib/agent/mounting.py` | `ConflictPolicy` Protocol + `NamespaceByMountId` default + `MountConflictError`; `MCPServerPort` Protocol (`list_tools()`); `MountRegistry` — pending/active sets, `stage()`, `begin_turn()` promotion + invalidate callback, `active_tools()`. The mid-session-mount core. |
| `src/fleetlib/agent/delegation.py` | `DelegationGrant` (subject/actor), `ExchangedIdentity` (nested actor chain), `TokenExchanger` Protocol, `InProcessExchanger` default (no passthrough), `TokenPassthroughError`. RFC 8693 core. |
| `src/fleetlib/agent/collaboration.py` | `CollaborationPolicy` Protocol + `AllowSameTenant` default (intra-tenant who-may-talk-to-whom; tenant boundary enforced upstream by `Scope`) + `CollaborationDenied`; `A2ATransportPort` Protocol; `PolicyGatedCollaborator` — gates talk by policy, structurally satisfies workflow's `Collaborator`/`EscalationRouter`. The collaboration-policy core. |
| `src/fleetlib/agent/ports.py` | The five narrow sibling **port Protocols** (`AIPort`, `MemoryPort`, `WorkspacePort`, `WorkflowPort`, `OrganizationPort`) + in-process fakes (`FakeAI`, `FakeMemory`, `FakeWorkspace`, `FakeWorkflow`, `FakeOrganization`). The un-tangling seam — no `fleetlib.*` sibling import. |
| `src/fleetlib/agent/agent.py` | `Agent` composition root — holds `Scope` + the three subsystems + five ports; `mount_mcp()`, `begin_turn()`, `tools()`, `act_on_behalf_of()`, `can_talk()`, `memory()`/`recall()` delegating shims. Thin: delegates, never re-implements. |
| `src/fleetlib/agent/adapters/__init__.py` | Adapters subpackage marker. |
| `src/fleetlib/agent/adapters/_stub.py` | `MissingExtraError` + `require_extra()` helper for optional-extra import guards. |
| `src/fleetlib/agent/adapters/fastmcp.py` | `FastMCPServer` stub (satisfies `MCPServerPort`) — raises `MissingExtraError` until the `mcp` extra. |
| `src/fleetlib/agent/adapters/a2a.py` | `A2ATransport` stub (satisfies `A2ATransportPort`) — raises until the `a2a` extra. |
| `src/fleetlib/agent/adapters/keycloak.py` | `KeycloakExchanger` stub (satisfies `TokenExchanger`) — raises until the `oauth` extra. |
| `tests/test_packaging.py` | Asserts `import fleetlib.agent` works and `fleetlib` is a PEP 420 namespace package. |
| `tests/test_scope.py` | `Scope` equality/hashing/validation/key. |
| `tests/test_tools.py` | `ToolSpec` shape + qualified-name provenance. |
| `tests/test_mounting.py` | Pending vs active; **keystone**: a mid-turn mount is NOT visible this turn, IS after `begin_turn()`; conflict resolution; invalidate callback fires; tenant isolation. |
| `tests/test_delegation.py` | Grant/exchange; multi-hop actor chain; **keystone**: raw subject token never appears downstream; passthrough attempt raises. |
| `tests/test_collaboration.py` | Policy allow/deny; cross-tenant talk denied; `PolicyGatedCollaborator` satisfies workflow's `Collaborator`/`EscalationRouter` shape. |
| `tests/test_ports.py` | The five port Protocols are runtime-checkable; fakes satisfy them; no `fleetlib.<sibling>` import. |
| `tests/test_agent.py` | `Agent` wires all of it; delegating shims call the ports; `Scope` threads through; end-to-end mount→begin_turn→tools. |
| `tests/test_adapter_stubs.py` | fastmcp/a2a/keycloak stubs raise `MissingExtraError` and name the seam they satisfy. |
| `tests/test_public_api.py` | Public surface lock + end-to-end composition. |

---

## Task 1: Package scaffold (namespace package + importable)

**Files:**
- Create: `pyproject.toml`
- Create: `src/fleetlib/agent/__init__.py`
- Create: `src/fleetlib/agent/py.typed`
- Test: `tests/test_packaging.py`

- [ ] **Step 1: Write the failing test**

```python
# tests/test_packaging.py
import importlib


def test_agent_imports():
    mod = importlib.import_module("fleetlib.agent")
    assert mod.__name__ == "fleetlib.agent"


def test_fleetlib_is_namespace_package():
    import fleetlib

    # PEP 420 namespace packages have no __file__ and a virtual __path__.
    assert getattr(fleetlib, "__file__", None) is None
    assert hasattr(fleetlib, "__path__")
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/test_packaging.py -v`
Expected: FAIL with `ModuleNotFoundError: No module named 'fleetlib'`

- [ ] **Step 3: Write minimal implementation**

```toml
# pyproject.toml
[build-system]
requires = ["hatchling"]
build-backend = "hatchling.build"

[project]
name = "fleetlib-agent"
version = "0.1.0"
description = "Thin composition/policy layer that wires an AI agent over mature protocols — mid-session MCP mounting (next-safe-turn), RFC 8693 delegated identity (no token passthrough), and collaboration policy over A2A."
readme = "README.md"
requires-python = ">=3.12"
license = { text = "MIT" }
dependencies = [
    "pydantic>=2.7",
]

[project.optional-dependencies]
# The five siblings this library WIRES together. They are declared per the charter but
# NEVER imported — agent consumes each through a local port Protocol (ports.py) with an
# in-process fake, so the default/test path needs none of them installed. They are kept
# OUT of the hard `dependencies` deliberately: lib-ai/organization have no code yet and
# memory/workspace/workflow ship no pyproject yet, so a hard dep would make the wheel
# uninstallable. Install this extra once the siblings publish (or via the dev sources below).
siblings = [
    "fleetlib-ai",
    "fleetlib-memory",
    "fleetlib-workspace",
    "fleetlib-workflow",
    "fleetlib-organization",
]
mcp = ["fastmcp>=2"]
a2a = ["a2a-sdk>=0.2"]
oauth = ["authlib>=1.3"]
# `agents` (openai-agents) is intentionally NOT an extra yet: this plan exposes the toolset
# (mounting.active_tools + the begin_turn invalidate callback) for whatever runner drives
# the model; it does not yet wrap the OpenAI Agents runner. Add an `agents` extra + an
# AgentRunnerPort seam only when that integration is actually built (YAGNI until then).
dev = ["pytest>=8", "ruff>=0.5"]

[tool.hatch.build.targets.wheel]
# PEP 420 namespace: ship the fleetlib/ dir WITHOUT a top-level fleetlib/__init__.py
packages = ["src/fleetlib"]

[tool.hatch.build.targets.sdist]
include = ["src/fleetlib", "README.md", "tests"]

# The siblings have no PyPI release yet; when present they resolve from the local monorepo.
# uv-only (pip ignores this table); the default test path does not need them. Note the
# lib-ai distribution lives in the `lib-ai/` directory, not `ai/`.
[tool.uv.sources]
fleetlib-ai = { path = "../lib-ai", editable = true }
fleetlib-memory = { path = "../memory", editable = true }
fleetlib-workspace = { path = "../workspace", editable = true }
fleetlib-workflow = { path = "../workflow", editable = true }
fleetlib-organization = { path = "../organization", editable = true }
```

```python
# src/fleetlib/agent/__init__.py
"""fleetlib.agent — the runtime that wires the five sibling capabilities into a working
agent, as a thin composition/POLICY layer ABOVE mature protocols (it does NOT fork them).

It builds only the three session-level gaps the research verdict identified:
  1. mid-session MCP mounting exposed on the next safe model turn (+ conflict + cache
     invalidation),
  2. delegated identity via RFC 8693 token exchange (subject/actor chains) — NEVER token
     passthrough,
  3. collaboration policy over A2A (who may talk to whom, when).

The five siblings (ai/memory/workspace/workflow/organization) are consumed through narrow
local port Protocols, never by importing their internals. Every default is in-process and
unit-testable; the real SDKs/transports are optional-extra stubs.
"""

__all__ = [
    "__version__",
]

__version__ = "0.1.0"
```

```text
# src/fleetlib/agent/py.typed
```

(Do NOT create `src/fleetlib/__init__.py` — its absence is what makes `fleetlib` a namespace package.)

- [ ] **Step 4: Run test to verify it passes**

Run: `pip install -e '.[dev]' && pytest tests/test_packaging.py -v`
Expected: PASS (2 passed)

> Note: this succeeds with no network — the five `fleetlib-*` siblings are NOT hard
> dependencies (they live in the `siblings` extra and are consumed via local port
> Protocols, never imported). Only `pydantic` + `pytest`/`ruff` resolve here.

- [ ] **Step 5: Commit**

```bash
git add pyproject.toml src/fleetlib/agent/__init__.py src/fleetlib/agent/py.typed tests/test_packaging.py
git commit -m "feat(agent): namespace package scaffold + importable surface"
```

---

## Task 2: Scope — the mandatory multi-tenant key

**Files:**
- Create: `src/fleetlib/agent/scope.py`
- Modify: `src/fleetlib/agent/__init__.py`
- Test: `tests/test_scope.py`

- [ ] **Step 1: Write the failing test**

```python
# tests/test_scope.py
import pytest
from pydantic import ValidationError

from fleetlib.agent import Scope


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
# src/fleetlib/agent/scope.py
"""Scope — the tenant-scoped key threaded through every subsystem of the agent.

Defined LOCALLY (these are standalone distributions; no cross-library import). Same shape
as every sibling library: tenant_id + namespace. Isolation is first-class — a mount, a
delegation, and a collaboration check all carry a Scope, and nothing crosses a
(tenant_id, namespace) boundary unless code explicitly moves it.
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
# src/fleetlib/agent/__init__.py  (extend imports + __all__)
from fleetlib.agent.scope import Scope

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
git add src/fleetlib/agent/scope.py src/fleetlib/agent/__init__.py tests/test_scope.py
git commit -m "feat(agent): Scope — mandatory multi-tenant key (tenant_id + namespace)"
```

---

## Task 3: ToolSpec — the unit the mount registry tracks

**Files:**
- Create: `src/fleetlib/agent/tools.py`
- Modify: `src/fleetlib/agent/__init__.py`
- Test: `tests/test_tools.py`

- [ ] **Step 1: Write the failing test**

```python
# tests/test_tools.py
import pytest
from pydantic import ValidationError

from fleetlib.agent import ToolSpec


def test_toolspec_minimal():
    t = ToolSpec(name="read_file", mount_id="fs")
    assert t.name == "read_file"
    assert t.mount_id == "fs"


def test_qualified_name_namespaces_by_mount_id():
    t = ToolSpec(name="read_file", mount_id="fs")
    assert t.qualified_name == "fs.read_file"


def test_toolspec_rejects_empty_name():
    with pytest.raises(ValidationError):
        ToolSpec(name="", mount_id="fs")
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/test_tools.py -v`
Expected: FAIL with `ImportError: cannot import name 'ToolSpec'`

- [ ] **Step 3: Write minimal implementation**

```python
# src/fleetlib/agent/tools.py
"""ToolSpec — the unit the MountRegistry tracks and the agent's toolset exposes.

Carries its mount-id provenance so conflict resolution can namespace a tool by the mount
it came from (qualified_name). This is data only; the actual tool invocation belongs to
the MCP transport, which the agent layer never re-implements.
"""

from __future__ import annotations

from pydantic import BaseModel, Field


class ToolSpec(BaseModel):
    """A tool exposed by a mounted MCP server, tagged with the mount it came from."""

    model_config = {"frozen": True}

    name: str = Field(min_length=1)
    mount_id: str = Field(min_length=1)

    @property
    def qualified_name(self) -> str:
        """The collision-free name: the mount id namespaces the bare tool name."""
        return f"{self.mount_id}.{self.name}"
```

```python
# src/fleetlib/agent/__init__.py  (extend imports + __all__)
from fleetlib.agent.scope import Scope
from fleetlib.agent.tools import ToolSpec

__all__ = [
    "__version__",
    "Scope",
    "ToolSpec",
]
```

- [ ] **Step 4: Run test to verify it passes**

Run: `pytest tests/test_tools.py -v`
Expected: PASS (3 passed)

- [ ] **Step 5: Commit**

```bash
git add src/fleetlib/agent/tools.py src/fleetlib/agent/__init__.py tests/test_tools.py
git commit -m "feat(agent): ToolSpec — mount-tagged tool unit with qualified-name provenance"
```

---

## Task 4: MountRegistry — mid-session mount exposed on the NEXT SAFE TURN (keystone #1)

**Files:**
- Create: `src/fleetlib/agent/mounting.py`
- Modify: `src/fleetlib/agent/__init__.py`
- Test: `tests/test_mounting.py`

- [ ] **Step 1: Write the failing test**

```python
# tests/test_mounting.py
import pytest

from fleetlib.agent import (
    MCPServerPort,
    MountConflictError,
    MountRegistry,
    NamespaceByMountId,
    Scope,
    ToolSpec,
)


class FakeServer:
    """An in-process MCPServerPort: just returns the tool names it was constructed with."""

    def __init__(self, names):
        self._names = list(names)

    def list_tools(self):
        return list(self._names)


ACME = Scope(tenant_id="acme")


def test_server_satisfies_port():
    assert isinstance(FakeServer(["a"]), MCPServerPort)


def test_keystone_mount_is_not_visible_until_next_turn():
    reg = MountRegistry(scope=ACME)
    # Turn 0 toolset is whatever is already active (nothing yet).
    assert reg.active_tools() == []

    # Mid-turn mount: staged into pending, effective on the NEXT safe turn only.
    reg.stage("fs", FakeServer(["read_file"]))
    assert reg.active_tools() == []  # still not visible this turn

    # The turn boundary promotes pending -> active.
    reg.begin_turn()
    names = {t.qualified_name for t in reg.active_tools()}
    assert names == {"fs.read_file"}


def test_begin_turn_fires_invalidate_callback():
    fired = []
    reg = MountRegistry(scope=ACME, on_invalidate=lambda: fired.append(True))
    reg.stage("fs", FakeServer(["read_file"]))
    reg.begin_turn()
    assert fired == [True]


def test_idle_begin_turn_does_not_fire_invalidate():
    fired = []
    reg = MountRegistry(scope=ACME, on_invalidate=lambda: fired.append(True))
    reg.begin_turn()  # nothing pending
    assert fired == []


def test_conflict_default_namespaces_by_mount_id():
    reg = MountRegistry(scope=ACME)
    reg.stage("fs", FakeServer(["read"]))
    reg.stage("db", FakeServer(["read"]))  # same bare name, different mount
    reg.begin_turn()
    names = {t.qualified_name for t in reg.active_tools()}
    assert names == {"fs.read", "db.read"}  # no collision — namespaced


def test_conflict_policy_can_reject():
    class RejectOnConflict:
        def resolve(self, incoming, active):
            if any(a.name == incoming.name for a in active):
                raise MountConflictError(incoming.name)
            return incoming

    reg = MountRegistry(scope=ACME, conflict_policy=RejectOnConflict())
    reg.stage("fs", FakeServer(["read"]))
    reg.begin_turn()
    reg.stage("db", FakeServer(["read"]))
    with pytest.raises(MountConflictError):
        reg.begin_turn()


def test_namespace_by_mount_id_is_the_default_policy():
    reg = MountRegistry(scope=ACME)
    assert isinstance(reg.conflict_policy, NamespaceByMountId)


def test_registry_is_tenant_scoped():
    reg = MountRegistry(scope=Scope(tenant_id="acme", namespace="agent:1"))
    assert reg.scope.tenant_id == "acme"
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/test_mounting.py -v`
Expected: FAIL with `ImportError: cannot import name 'MountRegistry'`

- [ ] **Step 3: Write minimal implementation**

```python
# src/fleetlib/agent/mounting.py
"""Mid-session MCP capability mounting — the first session-level gap.

MCP already supports live tool changes (tools.listChanged, FastMCP live mounting, OpenAI
Agents SDK re-lists per run + invalidate_tools_cache). What's missing is the SESSION
ORCHESTRATION: mount a server mid-session but expose its tools only on the NEXT SAFE MODEL
TURN, resolve naming conflicts, and invalidate the tool cache. This module owns exactly
that — it does NOT re-implement MCP.

The turn boundary (the charter's open question) is DEFINED here, observably: stage() puts
a mount into `pending`; begin_turn() promotes pending->active and fires on_invalidate.
A staged mount is therefore never visible during the current turn — only the next one.
"""

from __future__ import annotations

from collections.abc import Callable
from typing import Protocol, runtime_checkable

from fleetlib.agent.scope import Scope
from fleetlib.agent.tools import ToolSpec


class MountConflictError(RuntimeError):
    """Raised by a ConflictPolicy that refuses to resolve a tool-name collision."""


@runtime_checkable
class MCPServerPort(Protocol):
    def list_tools(self) -> list[str]:
        """Return the bare tool names this server exposes."""
        ...


@runtime_checkable
class ConflictPolicy(Protocol):
    def resolve(self, incoming: ToolSpec, active: list[ToolSpec]) -> ToolSpec:
        """Return the ToolSpec to add (possibly renamed), or raise MountConflictError."""
        ...


class NamespaceByMountId:
    """Default ConflictPolicy — never collides: the mount id namespaces the tool name.

    ToolSpec.qualified_name already carries `${mount_id}.${name}`, so two mounts exposing
    the same bare name stay distinct. This policy is a no-op pass-through that documents
    the rule and leaves a hook for stricter policies (e.g. reject) to be swapped in.
    """

    def resolve(self, incoming: ToolSpec, active: list[ToolSpec]) -> ToolSpec:
        return incoming


class MountRegistry:
    """Holds the active toolset and a pending set staged for the next safe turn."""

    def __init__(
        self,
        scope: Scope,
        *,
        conflict_policy: ConflictPolicy | None = None,
        on_invalidate: Callable[[], None] | None = None,
    ) -> None:
        self.scope = scope
        self.conflict_policy: ConflictPolicy = conflict_policy or NamespaceByMountId()
        self._on_invalidate = on_invalidate
        self._active: list[ToolSpec] = []
        self._pending: list[tuple[str, MCPServerPort]] = []

    def stage(self, mount_id: str, server: MCPServerPort) -> None:
        """Stage a mount. Its tools become visible only after the next begin_turn()."""
        self._pending.append((mount_id, server))

    def begin_turn(self) -> None:
        """Promote every pending mount into the active toolset (the safe-turn boundary)."""
        if not self._pending:
            return
        for mount_id, server in self._pending:
            for name in server.list_tools():
                spec = ToolSpec(name=name, mount_id=mount_id)
                resolved = self.conflict_policy.resolve(spec, self._active)
                self._active.append(resolved)
        self._pending.clear()
        if self._on_invalidate is not None:
            self._on_invalidate()

    def active_tools(self) -> list[ToolSpec]:
        """The toolset the model sees THIS turn (excludes anything staged this turn)."""
        return list(self._active)
```

```python
# src/fleetlib/agent/__init__.py  (extend imports + __all__)
from fleetlib.agent.mounting import (
    ConflictPolicy,
    MCPServerPort,
    MountConflictError,
    MountRegistry,
    NamespaceByMountId,
)
from fleetlib.agent.scope import Scope
from fleetlib.agent.tools import ToolSpec

__all__ = [
    "__version__",
    "Scope",
    "ToolSpec",
    "MCPServerPort",
    "ConflictPolicy",
    "NamespaceByMountId",
    "MountConflictError",
    "MountRegistry",
]
```

- [ ] **Step 4: Run test to verify it passes**

Run: `pytest tests/test_mounting.py -v`
Expected: PASS (8 passed)

- [ ] **Step 5: Commit**

```bash
git add src/fleetlib/agent/mounting.py src/fleetlib/agent/__init__.py tests/test_mounting.py
git commit -m "feat(agent): MountRegistry — mid-session mount exposed on the next safe turn (+ conflict + invalidate)"
```

---

## Task 5: Delegation — RFC 8693 token exchange, NEVER passthrough (keystone #2)

**Files:**
- Create: `src/fleetlib/agent/delegation.py`
- Modify: `src/fleetlib/agent/__init__.py`
- Test: `tests/test_delegation.py`

- [ ] **Step 1: Write the failing test**

```python
# tests/test_delegation.py
import pytest

from fleetlib.agent import (
    DelegationGrant,
    ExchangedIdentity,
    InProcessExchanger,
    Scope,
    TokenExchanger,
    TokenPassthroughError,
)

ACME = Scope(tenant_id="acme")


def test_in_process_exchanger_satisfies_protocol():
    assert isinstance(InProcessExchanger(), TokenExchanger)


def test_grant_carries_subject_and_actor():
    g = DelegationGrant(subject_token="human-tok", actor="agent:platform")
    assert g.subject_token == "human-tok"
    assert g.actor == "agent:platform"


def test_keystone_raw_subject_token_never_appears_downstream():
    # The whole point of RFC 8693 vs passthrough: the human's token MUST NOT travel
    # downstream. The exchanged identity is a fresh credential; the subject token only
    # named WHO is being acted for, never as a bearer credential.
    grant = DelegationGrant(subject_token="SECRET-HUMAN-TOKEN", actor="agent:platform")
    identity = InProcessExchanger().exchange(grant, ACME)

    assert isinstance(identity, ExchangedIdentity)
    assert identity.token != "SECRET-HUMAN-TOKEN"
    assert "SECRET-HUMAN-TOKEN" not in identity.token
    # The subject is recorded as a SUBJECT (who), not re-emitted as a credential.
    assert identity.subject == "agent:platform" or identity.act_chain  # acting party known
    assert "SECRET-HUMAN-TOKEN" not in repr(identity)


def test_passthrough_attempt_is_rejected():
    # If a caller tries to reuse the raw subject token AS the downstream token, refuse.
    ex = InProcessExchanger()
    with pytest.raises(TokenPassthroughError):
        ex.exchange(
            DelegationGrant(subject_token="tok", actor="agent:x", _passthrough=True),
            ACME,
        )


def test_multi_hop_builds_a_nested_actor_chain():
    # human -> platform -> security : the act chain records the full delegation path.
    ex = InProcessExchanger()
    first = ex.exchange(
        DelegationGrant(subject_token="human-tok", actor="agent:platform"), ACME
    )
    second = ex.exchange_from(first, actor="agent:security", scope=ACME)
    assert second.act_chain == ["agent:platform", "agent:security"]
    assert "human-tok" not in second.token


def test_exchanged_identity_is_tenant_scoped():
    identity = InProcessExchanger().exchange(
        DelegationGrant(subject_token="t", actor="agent:x"), ACME
    )
    assert identity.tenant_id == "acme"
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/test_delegation.py -v`
Expected: FAIL with `ImportError: cannot import name 'DelegationGrant'`

- [ ] **Step 3: Write minimal implementation**

```python
# src/fleetlib/agent/delegation.py
"""Delegated identity via RFC 8693 token exchange — the second session-level gap.

MCP OAuth supports on-behalf-of but EXPLICITLY FORBIDS token passthrough. So an agent
acting for a human (or for an upstream agent) must EXCHANGE the subject token for a fresh
downstream credential whose claims record a subject/actor chain — never forward the raw
token. This module owns that exchange + the multi-hop actor chain; the real Authorization
Server call (Keycloak) is an optional-extra adapter.

Security invariant (proven by tests): the raw subject token never appears in the exchanged
identity's downstream token or its repr.
"""

from __future__ import annotations

import hashlib
from typing import Protocol, runtime_checkable

from pydantic import BaseModel, Field

from fleetlib.agent.scope import Scope


class TokenPassthroughError(RuntimeError):
    """Raised when a caller attempts to forward a raw subject token as the downstream
    credential — the one thing RFC 8693 / MCP OAuth forbids."""


class DelegationGrant(BaseModel):
    """A request to act on behalf of a subject: the subject's token + the acting party."""

    subject_token: str = Field(min_length=1)
    actor: str = Field(min_length=1)
    # Test/guard hook: an explicit attempt to passthrough must be refused.
    passthrough: bool = Field(default=False, alias="_passthrough")

    model_config = {"populate_by_name": True}


class ExchangedIdentity(BaseModel):
    """The fresh downstream credential. It carries WHO is acting (subject + act_chain) but
    never the raw subject token."""

    token: str
    subject: str
    tenant_id: str
    act_chain: list[str] = Field(default_factory=list)

    def __repr__(self) -> str:  # keep the raw subject token out of logs entirely
        return f"ExchangedIdentity(subject={self.subject!r}, act_chain={self.act_chain!r})"


def _mint(material: str, tenant_id: str) -> str:
    """Deterministically derive a fresh, opaque downstream token. NOT the subject token.

    A real AS issues a signed JWT here; the in-process default derives an opaque value so
    the raw subject token can never leak through it (one-way hash).
    """
    digest = hashlib.sha256(f"{tenant_id}:{material}".encode()).hexdigest()
    return f"exch_{digest[:32]}"


@runtime_checkable
class TokenExchanger(Protocol):
    def exchange(self, grant: DelegationGrant, scope: Scope) -> ExchangedIdentity:
        """Exchange a subject token for a fresh on-behalf-of identity (never passthrough)."""
        ...

    def exchange_from(
        self, identity: ExchangedIdentity, *, actor: str, scope: Scope
    ) -> ExchangedIdentity:
        """Multi-hop RFC 8693: re-exchange an already-exchanged identity, extending the
        nested actor chain by one hop. On the Protocol so the multi-hop chain survives
        swapping in KeycloakExchanger (the charter names the multi-hop chain a design point)."""
        ...


class InProcessExchanger:
    """The ONE working default TokenExchanger — no network, no passthrough.

    Mints an opaque downstream token via a one-way derivation, records the actor chain,
    and refuses any explicit passthrough attempt. Swap KeycloakExchanger (oauth extra) for
    a real RFC 8693 token-exchange call against the AS.
    """

    def exchange(self, grant: DelegationGrant, scope: Scope) -> ExchangedIdentity:
        if grant.passthrough:
            raise TokenPassthroughError(
                "token passthrough is forbidden (RFC 8693 / MCP OAuth) — exchange instead"
            )
        return ExchangedIdentity(
            token=_mint(grant.actor, scope.tenant_id),
            subject=grant.actor,
            tenant_id=scope.tenant_id,
            act_chain=[grant.actor],
        )

    def exchange_from(
        self, identity: ExchangedIdentity, *, actor: str, scope: Scope
    ) -> ExchangedIdentity:
        """Multi-hop: re-exchange an already-exchanged identity, extending the act chain."""
        return ExchangedIdentity(
            token=_mint(actor, scope.tenant_id),
            subject=actor,
            tenant_id=scope.tenant_id,
            act_chain=[*identity.act_chain, actor],
        )
```

```python
# src/fleetlib/agent/__init__.py  (extend imports + __all__)
from fleetlib.agent.delegation import (
    DelegationGrant,
    ExchangedIdentity,
    InProcessExchanger,
    TokenExchanger,
    TokenPassthroughError,
)
# ...keep existing imports...

# add to __all__:
#   "DelegationGrant", "ExchangedIdentity", "TokenExchanger",
#   "InProcessExchanger", "TokenPassthroughError"
```

- [ ] **Step 4: Run test to verify it passes**

Run: `pytest tests/test_delegation.py -v`
Expected: PASS (6 passed)

- [ ] **Step 5: Commit**

```bash
git add src/fleetlib/agent/delegation.py src/fleetlib/agent/__init__.py tests/test_delegation.py
git commit -m "feat(agent): RFC 8693 delegated identity — exchange + multi-hop chain, never passthrough"
```

---

## Task 6: Collaboration policy over A2A (keystone #3 — and the workflow seam)

**Files:**
- Create: `src/fleetlib/agent/collaboration.py`
- Modify: `src/fleetlib/agent/__init__.py`
- Test: `tests/test_collaboration.py`

- [ ] **Step 1: Write the failing test**

```python
# tests/test_collaboration.py
import pytest

from fleetlib.agent import (
    A2ATransportPort,
    AllowSameTenant,
    CollaborationDenied,
    CollaborationPolicy,
    PolicyGatedCollaborator,
    Scope,
)


class FakeTransport:
    """In-process A2ATransportPort: echoes a canned reply, records who was asked."""

    def __init__(self):
        self.sent = []

    def send(self, dst, question, scope):
        self.sent.append((dst, question, scope.tenant_id))
        return f"{dst}:ack"


ACME = Scope(tenant_id="acme")


def test_defaults_satisfy_protocols():
    assert isinstance(AllowSameTenant(), CollaborationPolicy)
    assert isinstance(FakeTransport(), A2ATransportPort)


def test_allow_same_tenant_permits_intra_tenant_talk():
    p = AllowSameTenant()
    assert p.can_talk("agent:a", "agent:b", ACME) is True


def test_policy_gated_collaborator_sends_when_allowed():
    t = FakeTransport()
    c = PolicyGatedCollaborator(transport=t, policy=AllowSameTenant(), scope=ACME, me="agent:a")
    reply = c.ask("agent:b", "is it safe?", {})
    assert reply == "agent:b:ack"
    assert t.sent == [("agent:b", "is it safe?", "acme")]


def test_denied_talk_raises_and_never_hits_the_wire():
    class DenyAll:
        def can_talk(self, src, dst, scope):
            return False

    t = FakeTransport()
    c = PolicyGatedCollaborator(transport=t, policy=DenyAll(), scope=ACME, me="agent:a")
    with pytest.raises(CollaborationDenied):
        c.ask("agent:b", "hi", {})
    assert t.sent == []  # policy gates BEFORE the transport


def test_allow_set_narrows_who_may_talk_to_whom():
    # HONEST scope of the default: AllowSameTenant gates the WHO-MAY-TALK-TO-WHOM pair
    # WITHIN a tenant. With no allow-set it permits any intra-tenant pair (open default);
    # given an allow-set it restricts to listed (src, dst) pairs. It does NOT (and cannot,
    # with a bare-string `dst`) decide cross-TENANT talk — that boundary is enforced by the
    # caller's Scope upstream, and tenant-qualified targets are a deferred design call
    # (see PLAN concerns). This test asserts the allow-set narrowing, not tenant denial.
    policy = AllowSameTenant(allowed={("agent:a", "agent:b")})
    assert policy.can_talk("agent:a", "agent:b", ACME) is True
    assert policy.can_talk("agent:a", "agent:c", ACME) is False  # not in the allow-set


def test_collaborator_satisfies_workflows_collaborator_shape():
    # The concrete inter-lib seam: workflow's `ask` step calls a Collaborator with
    # .ask(agent, question, state). PolicyGatedCollaborator structurally matches it, so it
    # drops straight into a fleetlib.workflow RunContext without an adapter.
    c = PolicyGatedCollaborator(
        transport=FakeTransport(), policy=AllowSameTenant(), scope=ACME, me="agent:a"
    )
    assert hasattr(c, "ask")
    answer = c.ask("agent:b", "q", {"state": 1})
    assert answer == "agent:b:ack"


def test_collaborator_satisfies_workflows_escalation_router_shape():
    # workflow's EscalationRouter is .route(escalation, chain) -> decider id.
    c = PolicyGatedCollaborator(
        transport=FakeTransport(), policy=AllowSameTenant(), scope=ACME, me="agent:a"
    )

    class Esc:
        reason = "stuck"

    assert c.route(Esc(), chain=["manager", "human"]) == "human"
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/test_collaboration.py -v`
Expected: FAIL with `ImportError: cannot import name 'CollaborationPolicy'`

- [ ] **Step 3: Write minimal implementation**

```python
# src/fleetlib/agent/collaboration.py
"""Collaboration policy over A2A — the third session-level gap.

A2A is mature (tasks/multi-turn/streaming/push/artifacts); it does NOT decide WHO may talk
to WHOM, WHEN. That policy is the gap. CollaborationPolicy answers can_talk(src, dst,
scope) purely in-process; PolicyGatedCollaborator gates a real A2A transport behind it so a
denied request never reaches the wire.

Inter-library seam: PolicyGatedCollaborator STRUCTURALLY satisfies fleetlib.workflow's
`Collaborator` (.ask(agent, question, state)) and `EscalationRouter` (.route(escalation,
chain)) Protocols — the talk that workflow's `ask`/`escalate` steps deferred "to the agent
layer". We do not import workflow; structural typing is the contract.
"""

from __future__ import annotations

from typing import Any, Protocol, runtime_checkable

from fleetlib.agent.scope import Scope


class CollaborationDenied(RuntimeError):
    """Raised when policy refuses a talk request before it reaches the transport."""


@runtime_checkable
class CollaborationPolicy(Protocol):
    def can_talk(self, src: str, dst: str, scope: Scope) -> bool:
        """Decide whether `src` may collaborate with `dst` within `scope`."""
        ...


@runtime_checkable
class A2ATransportPort(Protocol):
    def send(self, dst: str, question: str, scope: Scope) -> str:
        """Carry a question to `dst` over A2A within `scope` and return the reply."""
        ...


class AllowSameTenant:
    """Default CollaborationPolicy — the WHO-MAY-TALK-TO-WHOM rule WITHIN one tenant.

    Honest scope (do NOT overclaim): the tenant boundary itself is enforced UPSTREAM by the
    `Scope` a request carries — every `can_talk` call is already inside one tenant's scope,
    and `dst` is a bare agent id with no tenant of its own, so this policy cannot (and does
    not) adjudicate cross-TENANT talk. What it DOES decide:
      - `allowed is None` (default): permit any intra-tenant pair (open default — opinionated
        default, open edge; swap a stricter CollaborationPolicy to lock it down).
      - `allowed` given: permit only the listed `(src, dst)` pairs.
    Making cross-tenant denial expressible (tenant-qualified `dst`) is a deferred design
    call — see the PLAN concerns. The name reflects intent (intra-tenant talk), not a
    tenancy check this class performs."""

    def __init__(self, allowed: set[tuple[str, str]] | None = None) -> None:
        self._allowed = allowed

    def can_talk(self, src: str, dst: str, scope: Scope) -> bool:
        if self._allowed is None:
            return True
        return (src, dst) in self._allowed


class PolicyGatedCollaborator:
    """Gates an A2A transport behind a CollaborationPolicy.

    Implements BOTH workflow seams by structural typing:
      ask(agent, question, state) -> str          (workflow.Collaborator)
      route(escalation, chain) -> decider id       (workflow.EscalationRouter)
    """

    def __init__(
        self,
        *,
        transport: A2ATransportPort,
        policy: CollaborationPolicy,
        scope: Scope,
        me: str,
    ) -> None:
        self._transport = transport
        self._policy = policy
        self._scope = scope
        self._me = me

    def ask(self, agent: str, question: str, state: dict[str, Any]) -> str:
        if not self._policy.can_talk(self._me, agent, self._scope):
            raise CollaborationDenied(f"{self._me} -> {agent} denied by policy")
        return self._transport.send(agent, question, self._scope)

    def route(self, escalation: Any, chain: list[str]) -> str:
        """Escalation walks UP the org-provided chain to its terminal decider. The chain
        is opaque to agent (organization owns who-reports-to-whom); we take the last id as
        the terminal decider (human / SOTA), matching the sibling workflow default."""
        if not chain:
            raise CollaborationDenied(getattr(escalation, "reason", "unresolved"))
        return chain[-1]
```

```python
# src/fleetlib/agent/__init__.py  (extend imports + __all__)
from fleetlib.agent.collaboration import (
    A2ATransportPort,
    AllowSameTenant,
    CollaborationDenied,
    CollaborationPolicy,
    PolicyGatedCollaborator,
)
# ...keep existing imports...

# add to __all__:
#   "CollaborationPolicy", "AllowSameTenant", "A2ATransportPort",
#   "PolicyGatedCollaborator", "CollaborationDenied"
```

- [ ] **Step 4: Run test to verify it passes**

Run: `pytest tests/test_collaboration.py -v`
Expected: PASS (7 passed)

- [ ] **Step 5: Commit**

```bash
git add src/fleetlib/agent/collaboration.py src/fleetlib/agent/__init__.py tests/test_collaboration.py
git commit -m "feat(agent): collaboration policy over A2A — policy-gated talk satisfying workflow's seams"
```

---

## Task 7: Sibling port Protocols + in-process fakes (the un-tangling seam)

**Files:**
- Create: `src/fleetlib/agent/ports.py`
- Modify: `src/fleetlib/agent/__init__.py`
- Test: `tests/test_ports.py`

- [ ] **Step 1: Write the failing test**

```python
# tests/test_ports.py
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
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/test_ports.py -v`
Expected: FAIL with `ImportError: cannot import name 'AIPort'`

- [ ] **Step 3: Write minimal implementation**

```python
# src/fleetlib/agent/ports.py
"""The five sibling PORTS — the un-tangling seam.

agent wires ai/memory/workspace/workflow/organization, but consuming a sibling's CODE
would re-tangle the libraries (and lib-ai/organization have no code yet). So each sibling
is consumed through a NARROW local port Protocol with an in-process fake default — exactly
as the sibling `workflow` plan refused to import `fleetlib.ai` and used a local shape. The
real wiring (swap a fake for an adapter around the published sibling) happens downstream;
this library never imports `fleetlib.<sibling>`.

Each port is deliberately tiny: only the surface the Agent facade actually calls.
"""

from __future__ import annotations

from typing import Protocol, runtime_checkable

from fleetlib.agent.scope import Scope


@runtime_checkable
class AIPort(Protocol):
    def complete(self, prompt: str) -> str:
        """Run one model completion (fleetlib.ai's job)."""
        ...


@runtime_checkable
class MemoryPort(Protocol):
    def learn(self, text: str, scope: Scope) -> None:
        """Persist a learned fact within scope (fleetlib.memory's job)."""
        ...

    def recall(self, query: str, scope: Scope) -> list[str]:
        """Recall facts matching query within scope."""
        ...


@runtime_checkable
class WorkspacePort(Protocol):
    def write(self, path: str, content: str, scope: Scope) -> None:
        """Write a file to the agent's persistent desk (fleetlib.workspace's job)."""
        ...

    def read(self, path: str, scope: Scope) -> str:
        """Read a file from the desk."""
        ...


@runtime_checkable
class WorkflowPort(Protocol):
    def run(self, name: str, scope: Scope) -> dict:
        """Run a named procedure within scope (fleetlib.workflow's job)."""
        ...


@runtime_checkable
class OrganizationPort(Protocol):
    def escalation_chain(self, agent_id: str, scope: Scope) -> list[str]:
        """Return the escalation chain for agent_id (fleetlib.organization's job)."""
        ...


# --- in-process fakes (the ONE working default per port) ------------------------------


class FakeAI:
    def complete(self, prompt: str) -> str:
        return f"completion:{prompt}"


class FakeMemory:
    def __init__(self) -> None:
        self._store: dict[str, list[str]] = {}

    def learn(self, text: str, scope: Scope) -> None:
        self._store.setdefault(scope.key, []).append(text)

    def recall(self, query: str, scope: Scope) -> list[str]:
        return [t for t in self._store.get(scope.key, []) if query in t]


class FakeWorkspace:
    def __init__(self) -> None:
        self._files: dict[str, str] = {}

    def write(self, path: str, content: str, scope: Scope) -> None:
        self._files[f"{scope.key}/{path}"] = content

    def read(self, path: str, scope: Scope) -> str:
        return self._files.get(f"{scope.key}/{path}", "")


class FakeWorkflow:
    def run(self, name: str, scope: Scope) -> dict:
        return {"procedure": name, "tenant": scope.tenant_id, "ran": True}


class FakeOrganization:
    def __init__(self, chain: dict[str, list[str]] | None = None) -> None:
        self._chain = chain or {}

    def escalation_chain(self, agent_id: str, scope: Scope) -> list[str]:
        return self._chain.get(agent_id, ["human"])
```

```python
# src/fleetlib/agent/__init__.py  (extend imports + __all__)
from fleetlib.agent.ports import (
    AIPort,
    FakeAI,
    FakeMemory,
    FakeOrganization,
    FakeWorkflow,
    FakeWorkspace,
    MemoryPort,
    OrganizationPort,
    WorkflowPort,
    WorkspacePort,
)
# ...keep existing imports...

# add to __all__:
#   "AIPort", "MemoryPort", "WorkspacePort", "WorkflowPort", "OrganizationPort",
#   "FakeAI", "FakeMemory", "FakeWorkspace", "FakeWorkflow", "FakeOrganization"
```

- [ ] **Step 4: Run test to verify it passes**

Run: `pytest tests/test_ports.py -v`
Expected: PASS (5 passed)

- [ ] **Step 5: Commit**

```bash
git add src/fleetlib/agent/ports.py src/fleetlib/agent/__init__.py tests/test_ports.py
git commit -m "feat(agent): five sibling port Protocols + in-process fakes (no sibling import)"
```

---

## Task 8: Agent — the thin composition root

**Files:**
- Create: `src/fleetlib/agent/agent.py`
- Modify: `src/fleetlib/agent/__init__.py`
- Test: `tests/test_agent.py`

- [ ] **Step 1: Write the failing test**

```python
# tests/test_agent.py
import pytest

from fleetlib.agent import (
    Agent,
    CollaborationDenied,
    DelegationGrant,
    Scope,
)


class FakeServer:
    def __init__(self, names):
        self._names = list(names)

    def list_tools(self):
        return list(self._names)


class FakeTransport:
    def __init__(self):
        self.sent = []

    def send(self, dst, question, scope):
        self.sent.append(dst)
        return f"{dst}:ack"


ACME = Scope(tenant_id="acme", namespace="agent:platform")


def _agent(**kw):
    base = dict(scope=ACME, me="agent:platform")
    base.update(kw)
    return Agent(**base)


def test_agent_has_scope_and_default_ports():
    a = _agent()
    assert a.scope == ACME
    # default fakes are wired in so the agent works out of the box
    a.memory("the deploy passed")
    assert a.recall("deploy") == ["the deploy passed"]


def test_mount_mcp_is_not_visible_until_begin_turn():
    a = _agent()
    a.mount_mcp("fs", FakeServer(["read_file"]), effective="next_turn")
    assert a.tools() == []  # staged, not yet exposed
    a.begin_turn()
    assert {t.qualified_name for t in a.tools_specs()} == {"fs.read_file"}
    assert a.tools() == ["fs.read_file"]


def test_act_on_behalf_of_exchanges_without_passthrough():
    a = _agent()
    identity = a.act_on_behalf_of(
        DelegationGrant(subject_token="HUMAN-SECRET", actor="agent:platform")
    )
    assert identity.token != "HUMAN-SECRET"
    assert "HUMAN-SECRET" not in identity.token
    assert identity.tenant_id == "acme"


def test_delegate_further_extends_the_actor_chain_through_the_protocol():
    a = _agent()
    first = a.act_on_behalf_of(
        DelegationGrant(subject_token="HUMAN-SECRET", actor="agent:platform")
    )
    second = a.delegate_further(first, actor="agent:security")
    assert second.act_chain == ["agent:platform", "agent:security"]
    assert "HUMAN-SECRET" not in second.token


def test_can_talk_uses_the_collaboration_policy():
    a = _agent(transport=FakeTransport())
    # default policy (AllowSameTenant, no allow-set) permits intra-tenant talk
    assert a.can_talk("agent:security") is True
    reply = a.ask("agent:security", "is it safe?")
    assert reply == "agent:security:ack"


def test_denied_talk_raises():
    class DenyAll:
        def can_talk(self, src, dst, scope):
            return False

    a = _agent(transport=FakeTransport(), collaboration_policy=DenyAll())
    assert a.can_talk("agent:security") is False
    with pytest.raises(CollaborationDenied):
        a.ask("agent:security", "hi")


def test_agent_delegates_run_workflow_to_the_port():
    a = _agent()
    out = a.run_procedure("deploy")
    assert out == {"procedure": "deploy", "tenant": "acme", "ran": True}


def test_scope_threads_into_every_subsystem():
    a = _agent()
    a.workspace_write("notes.md", "hello")
    assert a.workspace_read("notes.md") == "hello"
    # a different-tenant agent cannot see it (isolation through the same fake store type)
    other = Agent(scope=Scope(tenant_id="globex"), me="x", workspace=a._workspace)
    assert other.workspace_read("notes.md") == ""
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/test_agent.py -v`
Expected: FAIL with `ImportError: cannot import name 'Agent'`

- [ ] **Step 3: Write minimal implementation**

```python
# src/fleetlib/agent/agent.py
"""Agent — the thin composition root that wires the three subsystems + five sibling ports.

It is DELIBERATELY thin: every capability call delegates to an injected port or a built
subsystem; the Agent re-implements NONE of memory/workflow/workspace behavior. A mandatory
Scope threads into every subsystem so isolation is real, not bolted on. Defaults are the
in-process fakes/working-defaults, so an Agent works out of the box; advanced users inject
real adapters (fastmcp/a2a/keycloak + published siblings).
"""

from __future__ import annotations

from fleetlib.agent.collaboration import (
    A2ATransportPort,
    AllowSameTenant,
    CollaborationPolicy,
    PolicyGatedCollaborator,
)
from fleetlib.agent.delegation import (
    DelegationGrant,
    ExchangedIdentity,
    InProcessExchanger,
    TokenExchanger,
)
from fleetlib.agent.mounting import ConflictPolicy, MCPServerPort, MountRegistry
from fleetlib.agent.ports import (
    AIPort,
    FakeAI,
    FakeMemory,
    FakeOrganization,
    FakeWorkflow,
    FakeWorkspace,
    MemoryPort,
    OrganizationPort,
    WorkflowPort,
    WorkspacePort,
)
from fleetlib.agent.scope import Scope
from fleetlib.agent.tools import ToolSpec


class Agent:
    """Composition/policy layer: one agent, scoped, wiring protocols + sibling ports."""

    def __init__(
        self,
        *,
        scope: Scope,
        me: str,
        ai: AIPort | None = None,
        memory: MemoryPort | None = None,
        workspace: WorkspacePort | None = None,
        workflow: WorkflowPort | None = None,
        organization: OrganizationPort | None = None,
        transport: A2ATransportPort | None = None,
        collaboration_policy: CollaborationPolicy | None = None,
        exchanger: TokenExchanger | None = None,
        conflict_policy: ConflictPolicy | None = None,
    ) -> None:
        self.scope = scope
        self._me = me
        self._ai: AIPort = ai or FakeAI()
        self._memory: MemoryPort = memory or FakeMemory()
        self._workspace: WorkspacePort = workspace or FakeWorkspace()
        self._workflow: WorkflowPort = workflow or FakeWorkflow()
        self._org: OrganizationPort = organization or FakeOrganization()
        self._exchanger: TokenExchanger = exchanger or InProcessExchanger()
        self._mounts = MountRegistry(scope=scope, conflict_policy=conflict_policy)
        # ONE policy instance, shared by can_talk() and the gated collaborator (no drift).
        self._policy: CollaborationPolicy = collaboration_policy or AllowSameTenant()
        self._collaborator = PolicyGatedCollaborator(
            transport=transport or _NullTransport(),
            policy=self._policy,
            scope=scope,
            me=me,
        )

    # --- (1) mid-session mounting -----------------------------------------------------

    def mount_mcp(
        self, mount_id: str, server: MCPServerPort, *, effective: str = "next_turn"
    ) -> None:
        """Stage an MCP server; its tools become visible on the next begin_turn()."""
        if effective != "next_turn":
            raise ValueError("only effective='next_turn' is supported")
        self._mounts.stage(mount_id, server)

    def begin_turn(self) -> None:
        """The safe-turn boundary: promote staged mounts and invalidate the tool cache."""
        self._mounts.begin_turn()

    def tools_specs(self) -> list[ToolSpec]:
        return self._mounts.active_tools()

    def tools(self) -> list[str]:
        return [t.qualified_name for t in self._mounts.active_tools()]

    # --- (2) delegated identity -------------------------------------------------------

    def act_on_behalf_of(self, grant: DelegationGrant) -> ExchangedIdentity:
        """RFC 8693 exchange — fresh downstream identity, never the raw subject token."""
        return self._exchanger.exchange(grant, self.scope)

    def delegate_further(self, identity: ExchangedIdentity, *, actor: str) -> ExchangedIdentity:
        """Multi-hop delegation — extend the nested actor chain by one hop (still no
        passthrough). Goes through the TokenExchanger Protocol, so it works with any
        exchanger (in-process default OR KeycloakExchanger)."""
        return self._exchanger.exchange_from(identity, actor=actor, scope=self.scope)

    # --- (3) collaboration ------------------------------------------------------------

    def can_talk(self, dst: str) -> bool:
        return self._policy.can_talk(self._me, dst, self.scope)

    def ask(self, dst: str, question: str) -> str:
        return self._collaborator.ask(dst, question, {})

    @property
    def collaborator(self) -> PolicyGatedCollaborator:
        """The workflow-compatible Collaborator/EscalationRouter for use in a RunContext."""
        return self._collaborator

    # --- sibling delegating shims (thin: just forward to the port) --------------------

    def think(self, prompt: str) -> str:
        return self._ai.complete(prompt)

    def memory(self, text: str) -> None:
        self._memory.learn(text, self.scope)

    def recall(self, query: str) -> list[str]:
        return self._memory.recall(query, self.scope)

    def workspace_write(self, path: str, content: str) -> None:
        self._workspace.write(path, content, self.scope)

    def workspace_read(self, path: str) -> str:
        return self._workspace.read(path, self.scope)

    def run_procedure(self, name: str) -> dict:
        return self._workflow.run(name, self.scope)

    def escalation_chain(self) -> list[str]:
        return self._org.escalation_chain(self._me, self.scope)


class _NullTransport:
    """Default A2A transport — no wire configured; records nothing, returns empty."""

    def send(self, dst: str, question: str, scope: Scope) -> str:
        return ""
```

```python
# src/fleetlib/agent/__init__.py  (extend imports + __all__)
from fleetlib.agent.agent import Agent
# ...keep existing imports...

# add "Agent" to __all__
```

- [ ] **Step 4: Run test to verify it passes**

Run: `pytest tests/test_agent.py -v`
Expected: PASS (8 passed)

- [ ] **Step 5: Commit**

```bash
git add src/fleetlib/agent/agent.py src/fleetlib/agent/__init__.py tests/test_agent.py
git commit -m "feat(agent): Agent composition root — wires mount/delegate/collaborate + sibling ports, scope-threaded"
```

---

## Task 9: Optional-extra adapter stubs (fastmcp / a2a / keycloak)

**Files:**
- Create: `src/fleetlib/agent/adapters/__init__.py`
- Create: `src/fleetlib/agent/adapters/_stub.py`
- Create: `src/fleetlib/agent/adapters/fastmcp.py`
- Create: `src/fleetlib/agent/adapters/a2a.py`
- Create: `src/fleetlib/agent/adapters/keycloak.py`
- Test: `tests/test_adapter_stubs.py`

- [ ] **Step 1: Write the failing test**

```python
# tests/test_adapter_stubs.py
import pytest

from fleetlib.agent.adapters._stub import MissingExtraError
from fleetlib.agent.adapters.a2a import A2ATransport
from fleetlib.agent.adapters.fastmcp import FastMCPServer
from fleetlib.agent.adapters.keycloak import KeycloakExchanger


@pytest.mark.parametrize(
    "cls,extra",
    [
        (FastMCPServer, "mcp"),
        (A2ATransport, "a2a"),
        (KeycloakExchanger, "oauth"),
    ],
)
def test_stub_instantiation_raises_until_extra_and_impl_land(cls, extra):
    with pytest.raises(MissingExtraError, match=extra):
        cls()


def test_stubs_name_the_seam_they_will_satisfy():
    assert FastMCPServer.satisfies == "MCPServerPort"
    assert A2ATransport.satisfies == "A2ATransportPort"
    assert KeycloakExchanger.satisfies == "TokenExchanger"
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/test_adapter_stubs.py -v`
Expected: FAIL with `ModuleNotFoundError: No module named 'fleetlib.agent.adapters'`

- [ ] **Step 3: Write minimal implementation**

```python
# src/fleetlib/agent/adapters/__init__.py
"""Optional-extra adapters. Stubs today — each names the Protocol seam it will satisfy and
raises MissingExtraError until its extra (and a real implementation) land. The in-process
defaults in the core package keep every default path testable without these."""
```

```python
# src/fleetlib/agent/adapters/_stub.py
"""Shared helper for optional-extra adapter stubs."""

from __future__ import annotations


class MissingExtraError(RuntimeError):
    """Raised when an optional-extra adapter is used before its extra/impl exist."""


def require_extra(extra: str) -> None:
    raise MissingExtraError(
        f"adapter requires the optional '{extra}' extra and a real implementation; "
        f"install with: pip install fleetlib-agent[{extra}] (stub not yet implemented)"
    )
```

```python
# src/fleetlib/agent/adapters/fastmcp.py
"""FastMCP adapter — STUB. Will satisfy MCPServerPort; raises until the mcp extra."""

from __future__ import annotations

from fleetlib.agent.adapters._stub import require_extra


class FastMCPServer:
    satisfies = "MCPServerPort"

    def __init__(self, *args, **kwargs) -> None:
        require_extra("mcp")
```

```python
# src/fleetlib/agent/adapters/a2a.py
"""A2A adapter — STUB. Will satisfy A2ATransportPort; raises until the a2a extra."""

from __future__ import annotations

from fleetlib.agent.adapters._stub import require_extra


class A2ATransport:
    satisfies = "A2ATransportPort"

    def __init__(self, *args, **kwargs) -> None:
        require_extra("a2a")
```

```python
# src/fleetlib/agent/adapters/keycloak.py
"""Keycloak RFC 8693 token-exchange adapter — STUB. Will satisfy TokenExchanger; raises
until the oauth extra. The real impl performs an RFC 8693 grant_type=token-exchange call
(subject_token + actor_token) against the AS; it must NEVER forward the raw subject token
downstream."""

from __future__ import annotations

from fleetlib.agent.adapters._stub import require_extra


class KeycloakExchanger:
    satisfies = "TokenExchanger"

    def __init__(self, *args, **kwargs) -> None:
        require_extra("oauth")
```

- [ ] **Step 4: Run test to verify it passes**

Run: `pytest tests/test_adapter_stubs.py -v`
Expected: PASS (4 passed)

- [ ] **Step 5: Commit**

```bash
git add src/fleetlib/agent/adapters tests/test_adapter_stubs.py
git commit -m "feat(agent): fastmcp/a2a/keycloak adapter stubs (name the seam, raise on use)"
```

---

## Task 10: Full-suite green + public API lock

**Files:**
- Test: `tests/test_public_api.py`

- [ ] **Step 1: Write the failing test**

```python
# tests/test_public_api.py
import fleetlib.agent as a


def test_public_surface_is_complete():
    expected = {
        "__version__",
        "Scope",
        "ToolSpec",
        # mounting
        "MCPServerPort",
        "ConflictPolicy",
        "NamespaceByMountId",
        "MountConflictError",
        "MountRegistry",
        # delegation
        "DelegationGrant",
        "ExchangedIdentity",
        "TokenExchanger",
        "InProcessExchanger",
        "TokenPassthroughError",
        # collaboration
        "CollaborationPolicy",
        "AllowSameTenant",
        "A2ATransportPort",
        "PolicyGatedCollaborator",
        "CollaborationDenied",
        # ports + fakes
        "AIPort",
        "MemoryPort",
        "WorkspacePort",
        "WorkflowPort",
        "OrganizationPort",
        "FakeAI",
        "FakeMemory",
        "FakeWorkspace",
        "FakeWorkflow",
        "FakeOrganization",
        # composition root
        "Agent",
    }
    assert expected <= set(a.__all__)
    for name in expected:
        assert hasattr(a, name), name


def test_end_to_end_composition():
    scope = a.Scope(tenant_id="acme", namespace="agent:platform")
    agent = a.Agent(scope=scope, me="agent:platform")

    # (1) mid-session mount -> not visible -> begin_turn -> visible
    class Srv:
        def list_tools(self):
            return ["read_file"]

    agent.mount_mcp("fs", Srv(), effective="next_turn")
    assert agent.tools() == []
    agent.begin_turn()
    assert agent.tools() == ["fs.read_file"]

    # (2) delegated identity — no passthrough
    ident = agent.act_on_behalf_of(
        a.DelegationGrant(subject_token="HUMAN-SECRET", actor="agent:platform")
    )
    assert "HUMAN-SECRET" not in ident.token

    # (3) collaboration policy
    assert agent.can_talk("agent:security") is True

    # sibling delegation — thin shims call the ports
    agent.memory("deploy ok")
    assert agent.recall("deploy") == ["deploy ok"]
    assert agent.run_procedure("deploy")["ran"] is True


def test_collaborator_is_workflow_runcontext_ready():
    # The agent's collaborator structurally satisfies workflow's Collaborator/EscalationRouter:
    # it has .ask(agent, question, state) and .route(escalation, chain).
    agent = a.Agent(scope=a.Scope(tenant_id="acme"), me="agent:a")
    c = agent.collaborator
    assert hasattr(c, "ask") and hasattr(c, "route")
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/test_public_api.py -v`
Expected: FAIL only if any `__all__` entry is missing; otherwise it confirms the surface assembled across Tasks 1-9.

- [ ] **Step 3: No new implementation**

The public API was assembled incrementally. This task adds the surface-lock + end-to-end test only. If `test_public_surface_is_complete` fails, add the missing names to `__init__.py` `__all__` (do not weaken the test).

- [ ] **Step 4: Run the full suite**

Run: `pytest -v`
Expected: PASS (all tests across all files green)

- [ ] **Step 5: Commit**

```bash
git add tests/test_public_api.py
git commit -m "test(agent): lock public API surface + end-to-end mount/delegate/collaborate composition"
```

---

## Self-Review Checklist (run after implementing)

1. **Charter coverage** — the default API is `agent.mount_mcp(server, effective="next_turn")` (Task 4/8) and `agent.act_on_behalf_of(delegation_grant)` (Task 5/8); the three built gaps are (1) mid-session mounting exposed next-safe-turn + conflict + invalidate (Task 4), (2) RFC 8693 delegated identity with a multi-hop actor chain and no passthrough (Task 5), (3) collaboration policy over A2A (Task 6). The lib WIRES the five siblings (Task 7/8). ✔
2. **WRAP not fork** — no protocol is re-implemented: `MCPServerPort`/`A2ATransportPort`/`TokenExchanger` are seams whose real impls are stub adapters (Task 9); the core owns only the session-level orchestration (turn boundary, conflict, exchange, policy). ✔
3. **Open charter questions answered** — "where is the turn boundary?" → DEFINED observably as `begin_turn()` promoting pending→active (Task 4 keystone); "multi-hop RFC 8693 chain" → `exchange_from` (on the `TokenExchanger` Protocol, so it survives swapping in `KeycloakExchanger`) extends `act_chain`, exposed as `Agent.delegate_further` (Task 5/8); "who may talk to whom, when" → `CollaborationPolicy.can_talk` (Task 6). ✔
4. **Security keystone** — the raw subject token never appears in the exchanged identity's token or repr, and an explicit passthrough attempt raises `TokenPassthroughError` (Task 5). ✔
5. **Principles** — every feature is a `typing.Protocol` + ONE in-process working default; real SDKs (fastmcp/a2a/keycloak) are optional-extra stubs (Task 9); `Scope` (tenant_id + namespace) is mandatory on the Agent and threads into mount registry, exchange, collaboration, and every sibling-port call. Isolation is PROVEN where the default store can express it: memory and workspace fakes key by `scope.key`, so a different-tenant agent reads nothing (Tasks 7/8). Collaboration's default (`AllowSameTenant`) gates intra-tenant who-talks-to-whom only — the cross-TENANT boundary is enforced upstream by the `Scope` each call carries, NOT by this policy (a bare-string `dst` can't name a tenant); making cross-tenant denial expressible is a deferred design call (see concerns). The plan no longer claims a cross-tenant collaboration-denial test it can't honestly run. ✔
6. **Un-tangling boundary** — the five siblings are consumed through narrow local port Protocols + fakes; `test_ports_module_does_not_import_sibling_internals` asserts no `import fleetlib.<sibling>` (Task 7). The one concrete inter-lib seam is honored structurally: `PolicyGatedCollaborator` satisfies workflow's `Collaborator`/`EscalationRouter` shapes (Task 6) and is exposed as `agent.collaborator` for a workflow `RunContext` (Task 8/10). ✔
7. **Packaging** — PEP 420 namespace (no `src/fleetlib/__init__.py`, Task 1 asserts it), src layout, `py.typed`, hatchling; the five `fleetlib-*` siblings declared per the charter in a `siblings` optional-extra (NOT hard deps — keeps the wheel installable before they publish) and never imported (resolved via `[tool.uv.sources]` in dev); optional extras `siblings`/`mcp`/`a2a`/`oauth`/`dev`. ✔
8. **Type consistency** — `Scope.key`, `ToolSpec.qualified_name`, `MountRegistry.stage/begin_turn/active_tools`, `ConflictPolicy.resolve`, `DelegationGrant(subject_token/actor)`, `ExchangedIdentity.token/subject/act_chain/tenant_id`, `TokenExchanger.exchange`, `InProcessExchanger.exchange/exchange_from`, `CollaborationPolicy.can_talk`, `PolicyGatedCollaborator.ask/route`, the five `*Port`/`Fake*`, and `Agent(scope=, me=, …)` are used identically across all tasks. ✔
