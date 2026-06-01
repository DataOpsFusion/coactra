# fleetlib.workspace Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Ship a publishable, thin control layer — the persistent **agent desk** — OVER swappable sandbox backends. `Workspace` gives an agent `write` / `read` / `run` (CLI-policy-gated) / `handoff` (day-note) / `compact` (auto-compact) / a stored capability **manifest reference**, all scoped per `(tenant_id, agent_id)` and persistent by default, over a `WorkspaceBackend` Protocol with ONE working default (`LocalFilesystemBackend`).

**Architecture:** Two layers. (1) `WorkspaceBackend` `typing.Protocol` — the dumb, swappable persistence + exec primitive: `write_file` / `read_file` / `list_files` / `delete_file` / `exec`, all rooted at a desk path it confines. The ONE working default is `LocalFilesystemBackend` (a persistent dir per `tenant_id/agent_id`); Daytona / E2B / OpenHands are optional-extra **stubs**. (2) `Workspace` facade — the "desk": wraps a backend + a `Scope`, and layers the charter value-add ON TOP — `run()` enforces `CliPolicy` then delegates to `backend.exec`; `handoff()`/`day_note()` persist a hand-off note; `compact()` caps the day-note by deterministic rules (no LLM, no `lib-ai`); `set_manifest()`/`manifest()` store a **passive** `CapabilityManifest` reference (workspace STORES it; the agent runtime does the actual MCP mounting). Boundary lines are load-bearing: no `mount()`, no roles/escalation, no summarizer dep.

**Tech Stack:** Python 3.12+, pydantic v2, hatchling (PEP 420 namespace package `fleetlib/workspace/`, src layout), pytest. Runtime dep: `pydantic` only (sibling lib — depends on nothing else). Optional extras: `daytona` (`daytona-sdk`), `e2b` (`e2b`), `openhands` (no pinned dep — stub only), `dev`. Persistent by default; ephemeral is an opt-in mode.

---

## File Structure

| File | Single responsibility |
|------|----------------------|
| `pyproject.toml` | Distribution `fleetlib-workspace`; hatchling targets the `fleetlib` namespace dir; runtime dep `pydantic`; `[project.optional-dependencies]` for `daytona`/`e2b`/`openhands`/`dev`. |
| `src/fleetlib/workspace/__init__.py` | Public API surface — re-exports `Scope`, `ExecResult`, `CliPolicy`, `PolicyError`, `CapabilityManifest`, `WorkspaceBackend`, `LocalFilesystemBackend`, `Workspace`, `open_workspace`. NO `src/fleetlib/__init__.py` (namespace package). |
| `src/fleetlib/workspace/py.typed` | PEP 561 typing marker. |
| `src/fleetlib/workspace/scope.py` | `Scope` value object — `tenant_id` + `agent_id`; the per-agent/per-tenant key threaded through every call. |
| `src/fleetlib/workspace/models.py` | `ExecResult` (exit_code/stdout/stderr) and `CapabilityManifest` (passive list of capability refs the agent runtime re-mounts). |
| `src/fleetlib/workspace/policy.py` | `CliPolicy` — desk-local allow/deny command gate + `PolicyError`; NOT org policy. |
| `src/fleetlib/workspace/backend.py` | `WorkspaceBackend` `typing.Protocol` — `root_for()`, `write_file()`, `read_file()`, `list_files()`, `delete_file()`, `exec()`. |
| `src/fleetlib/workspace/local.py` | `LocalFilesystemBackend` — the ONE working default: persistent dir per scope, path-traversal confinement, real subprocess exec rooted at the desk. |
| `src/fleetlib/workspace/desk.py` | `Workspace` facade + `open_workspace()` factory — write/read/run(policy)/handoff/day_note/compact/manifest, all scope-bound; ephemeral mode. |
| `src/fleetlib/workspace/adapters/__init__.py` | Adapters subpackage marker. |
| `src/fleetlib/workspace/adapters/_stub.py` | `MissingExtraError` + `require_extra()` helper for optional-extra import guards. |
| `src/fleetlib/workspace/adapters/daytona.py` | `DaytonaBackend` stub — raises `MissingExtraError` until the `daytona` extra + real impl land. |
| `src/fleetlib/workspace/adapters/e2b.py` | `E2BBackend` stub — raises until the `e2b` extra. |
| `src/fleetlib/workspace/adapters/openhands.py` | `OpenHandsBackend` stub — raises until the `openhands` extra. |
| `tests/test_packaging.py` | Asserts `import fleetlib.workspace` works and `fleetlib` is a PEP 420 namespace package. |
| `tests/test_scope.py` | `Scope` equality/hashing/validation + per-agent key. |
| `tests/test_models.py` | `ExecResult` shape; `CapabilityManifest` is passive data (no `mount()`). |
| `tests/test_policy.py` | Allow/deny gate raises `PolicyError` and never reaches exec. |
| `tests/test_backend_protocol.py` | `WorkspaceBackend` is `runtime_checkable`; a complete dummy satisfies it, an incomplete class does not. |
| `tests/test_local_files.py` | LocalFilesystemBackend write/read/list/delete + traversal confinement. |
| `tests/test_local_exec.py` | LocalFilesystemBackend exec runs rooted at the desk, returns `ExecResult`. |
| `tests/test_isolation.py` | Tenant A / agent A cannot see tenant B / agent B's desk. |
| `tests/test_desk.py` | Facade write/read/run-with-policy + manifest round-trip (no mount). |
| `tests/test_handoff_compact.py` | Day-note handoff persists; compact caps it by rule (no LLM). |
| `tests/test_persistence.py` | Persistent by default across instances; ephemeral mode does NOT persist. |
| `tests/test_adapter_stubs.py` | Daytona/E2B/OpenHands stubs import without the extra but raise `MissingExtraError` on use. |
| `tests/test_public_api.py` | Public surface lock + end-to-end open/write/run/handoff. |

---

## Task 1: Package scaffold (namespace package + importable)

**Files:**
- Create: `pyproject.toml`
- Create: `src/fleetlib/workspace/__init__.py`
- Create: `src/fleetlib/workspace/py.typed`
- Test: `tests/test_packaging.py`

- [ ] **Step 1: Write the failing test**

```python
# tests/test_packaging.py
import importlib


def test_workspace_imports():
    mod = importlib.import_module("fleetlib.workspace")
    assert mod is not None


def test_fleetlib_is_namespace_package():
    import fleetlib

    # PEP 420 namespace packages have no __file__ and expose a virtual __path__.
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
name = "fleetlib-workspace"
version = "0.1.0"
description = "The persistent agent desk — a thin control layer over swappable sandbox backends (files / CLI policy / handoff / auto-compact / capability manifest)."
readme = "README.md"
requires-python = ">=3.12"
license = { text = "MIT" }
dependencies = ["pydantic>=2.7"]

[project.optional-dependencies]
daytona = ["daytona-sdk>=0.10"]
e2b = ["e2b>=1.0"]
openhands = []  # no pinned dep yet; stub adapter only
dev = ["pytest>=8"]

[tool.hatch.build.targets.wheel]
# PEP 420 namespace: ship the fleetlib/ dir WITHOUT a top-level fleetlib/__init__.py
packages = ["src/fleetlib"]

[tool.hatch.build.targets.sdist]
include = ["src/fleetlib", "README.md", "tests"]
```

```python
# src/fleetlib/workspace/__init__.py
"""fleetlib.workspace — the persistent agent desk.

A thin control layer ABOVE persistent sandbox backends (local filesystem by default;
Daytona / E2B / OpenHands optional). The backend persists files + runs commands; this
layer adds the "desk": scoped files, a CLI policy gate, a handoff/day-note, rule-based
auto-compact, and storage for a capability-manifest REFERENCE. It does NOT mount MCP
capabilities (the agent runtime does) and does NOT own hierarchy/policy (organization does).
"""

__all__ = [
    "__version__",
]

__version__ = "0.1.0"
```

```text
# src/fleetlib/workspace/py.typed
```

(Do NOT create `src/fleetlib/__init__.py` — its absence is what makes `fleetlib` a namespace package.)

- [ ] **Step 4: Run test to verify it passes**

Run: `pip install -e . && pytest tests/test_packaging.py -v`
Expected: PASS (2 passed)

> **Must be run, not assumed.** PEP 420 + hatchling *editable* installs do not always
> yield `fleetlib.__file__ is None` (a `.pth` redirect vs. an import-hook finder differ).
> If `test_fleetlib_is_namespace_package` fails here, the robust fix is to drop the
> `__file__ is None` assertion and instead assert `fleetlib.__path__` is a namespace path
> (e.g. `not isinstance(fleetlib.__path__, list)` / `"fleetlib" in repr(fleetlib.__path__)`).
> Resolve this at Task 1 before building on top of it.

- [ ] **Step 5: Commit**

```bash
git add pyproject.toml src/fleetlib/workspace/__init__.py src/fleetlib/workspace/py.typed tests/test_packaging.py
git commit -m "feat(workspace): namespace package scaffold + importable surface"
```

---

## Task 2: Scope — the per-tenant / per-agent desk key

**Files:**
- Create: `src/fleetlib/workspace/scope.py`
- Modify: `src/fleetlib/workspace/__init__.py`
- Test: `tests/test_scope.py`

- [ ] **Step 1: Write the failing test**

```python
# tests/test_scope.py
import pytest
from pydantic import ValidationError

from fleetlib.workspace import Scope


def test_scope_fields():
    s = Scope(tenant_id="acme", agent_id="planner")
    assert s.tenant_id == "acme"
    assert s.agent_id == "planner"


def test_scope_is_hashable_and_equal():
    a = Scope(tenant_id="acme", agent_id="planner")
    b = Scope(tenant_id="acme", agent_id="planner")
    assert a == b
    assert hash(a) == hash(b)
    assert {a, b} == {a}


def test_scope_rejects_empty_parts():
    with pytest.raises(ValidationError):
        Scope(tenant_id="", agent_id="planner")
    with pytest.raises(ValidationError):
        Scope(tenant_id="acme", agent_id="")


def test_scope_key_is_stable_relative_path():
    assert Scope(tenant_id="acme", agent_id="planner").key == "acme/planner"
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/test_scope.py -v`
Expected: FAIL with `ImportError: cannot import name 'Scope'`

- [ ] **Step 3: Write minimal implementation**

```python
# src/fleetlib/workspace/scope.py
"""Scope — the per-tenant / per-agent desk key threaded through every workspace call.

The charter names the dimensions explicitly: a desk is "per agent/tenant". Isolation is
first-class: a backend roots each desk at <base>/<tenant_id>/<agent_id>/, and nothing
crosses that boundary. agent_id is NOT collapsed into a generic namespace — the per-agent
desk is named in the charter.
"""

from __future__ import annotations

from pydantic import BaseModel, Field


class Scope(BaseModel):
    """Immutable, hashable tenant + agent key for one desk."""

    model_config = {"frozen": True}

    tenant_id: str = Field(min_length=1)
    agent_id: str = Field(min_length=1)

    @property
    def key(self) -> str:
        return f"{self.tenant_id}/{self.agent_id}"
```

```python
# src/fleetlib/workspace/__init__.py  (extend imports + __all__)
from fleetlib.workspace.scope import Scope

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
git add src/fleetlib/workspace/scope.py src/fleetlib/workspace/__init__.py tests/test_scope.py
git commit -m "feat(workspace): Scope — per-tenant/per-agent desk key"
```

---

## Task 3: Models — ExecResult + passive CapabilityManifest

**Files:**
- Create: `src/fleetlib/workspace/models.py`
- Modify: `src/fleetlib/workspace/__init__.py`
- Test: `tests/test_models.py`

- [ ] **Step 1: Write the failing test**

```python
# tests/test_models.py
from fleetlib.workspace import CapabilityManifest, ExecResult


def test_exec_result_fields():
    r = ExecResult(exit_code=0, stdout="hi\n", stderr="")
    assert r.exit_code == 0
    assert r.ok is True
    assert r.stdout == "hi\n"


def test_exec_result_nonzero_is_not_ok():
    assert ExecResult(exit_code=1, stdout="", stderr="boom").ok is False


def test_manifest_is_passive_data_only():
    # The agent runtime mounts MCP capabilities; workspace only STORES the reference.
    m = CapabilityManifest(refs=["mcp://gateway/search_tools", "mcp://gateway/call_tool"])
    assert m.refs[0] == "mcp://gateway/search_tools"
    # Boundary lock: no mount/connect/activate behavior lives on the manifest.
    assert not hasattr(m, "mount")
    assert not hasattr(m, "connect")
    assert not hasattr(m, "activate")


def test_manifest_defaults_empty():
    assert CapabilityManifest().refs == []
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/test_models.py -v`
Expected: FAIL with `ImportError: cannot import name 'CapabilityManifest'`

- [ ] **Step 3: Write minimal implementation**

```python
# src/fleetlib/workspace/models.py
"""Workspace data models.

ExecResult        — the typed result of a desk command (exit_code / stdout / stderr).
CapabilityManifest — a PASSIVE list of capability references the agent runtime re-mounts.
                     workspace STORES this so the next session knows what to re-mount; it
                     never mounts anything itself (no mount/connect/activate). That boundary
                     is the charter's: "the agent runtime does MCP mounting (workspace only
                     STORES the capability manifest reference)."
"""

from __future__ import annotations

from pydantic import BaseModel, Field


class ExecResult(BaseModel):
    """The typed result of running a command on the desk."""

    exit_code: int
    stdout: str = ""
    stderr: str = ""

    @property
    def ok(self) -> bool:
        return self.exit_code == 0


class CapabilityManifest(BaseModel):
    """Passive reference list of capabilities the agent runtime should mount. Data only."""

    refs: list[str] = Field(default_factory=list)
```

```python
# src/fleetlib/workspace/__init__.py  (extend imports + __all__)
from fleetlib.workspace.models import CapabilityManifest, ExecResult
from fleetlib.workspace.scope import Scope

__all__ = [
    "__version__",
    "Scope",
    "ExecResult",
    "CapabilityManifest",
]
```

- [ ] **Step 4: Run test to verify it passes**

Run: `pytest tests/test_models.py -v`
Expected: PASS (4 passed)

- [ ] **Step 5: Commit**

```bash
git add src/fleetlib/workspace/models.py src/fleetlib/workspace/__init__.py tests/test_models.py
git commit -m "feat(workspace): ExecResult + passive CapabilityManifest (no mount)"
```

---

## Task 4: CliPolicy — the desk-local command gate

**Files:**
- Create: `src/fleetlib/workspace/policy.py`
- Modify: `src/fleetlib/workspace/__init__.py`
- Test: `tests/test_policy.py`

- [ ] **Step 1: Write the failing test**

```python
# tests/test_policy.py
import pytest

from fleetlib.workspace import CliPolicy, PolicyError


def test_default_policy_allows_everything():
    pol = CliPolicy()
    pol.check("ls -la")  # no raise


def test_deny_blocks_matching_command():
    pol = CliPolicy(deny=["rm"])
    pol.check("ls")  # allowed
    with pytest.raises(PolicyError, match="rm"):
        pol.check("rm -rf /")


def test_allowlist_blocks_anything_not_listed():
    pol = CliPolicy(allow=["ls", "cat"])
    pol.check("ls -la")
    pol.check("cat notes.md")
    with pytest.raises(PolicyError, match="curl"):
        pol.check("curl http://evil")


def test_deny_takes_precedence_over_allow():
    pol = CliPolicy(allow=["git"], deny=["git push"])
    pol.check("git status")
    with pytest.raises(PolicyError):
        pol.check("git push origin main")


def test_empty_command_is_rejected():
    with pytest.raises(PolicyError):
        CliPolicy().check("   ")
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/test_policy.py -v`
Expected: FAIL with `ImportError: cannot import name 'CliPolicy'`

- [ ] **Step 3: Write minimal implementation**

```python
# src/fleetlib/workspace/policy.py
"""CliPolicy — a desk-LOCAL command allow/deny gate.

This is the charter's "CLI policy": which commands the agent may run inside its own desk.
It is NOT organization policy — no roles, no escalation, no reporting (organization owns
that). Matching is a simple prefix/substring check on the command string: deny wins over
allow; an allowlist (when set) is default-deny.
"""

from __future__ import annotations

from pydantic import BaseModel, Field


class PolicyError(RuntimeError):
    """Raised when a command is blocked by the desk CLI policy."""


class CliPolicy(BaseModel):
    """Allow/deny gate evaluated before a command reaches the backend."""

    allow: list[str] = Field(default_factory=list)  # empty => allow all (subject to deny)
    deny: list[str] = Field(default_factory=list)

    def check(self, command: str) -> None:
        cmd = command.strip()
        if not cmd:
            raise PolicyError("empty command is not allowed")
        for pattern in self.deny:
            if pattern in cmd:
                raise PolicyError(f"command blocked by deny rule: {pattern!r}")
        if self.allow and not any(cmd.startswith(p) for p in self.allow):
            raise PolicyError(f"command not in allowlist: {cmd!r}")
```

```python
# src/fleetlib/workspace/__init__.py  (extend imports + __all__)
from fleetlib.workspace.models import CapabilityManifest, ExecResult
from fleetlib.workspace.policy import CliPolicy, PolicyError
from fleetlib.workspace.scope import Scope

__all__ = [
    "__version__",
    "Scope",
    "ExecResult",
    "CapabilityManifest",
    "CliPolicy",
    "PolicyError",
]
```

- [ ] **Step 4: Run test to verify it passes**

Run: `pytest tests/test_policy.py -v`
Expected: PASS (5 passed)

- [ ] **Step 5: Commit**

```bash
git add src/fleetlib/workspace/policy.py src/fleetlib/workspace/__init__.py tests/test_policy.py
git commit -m "feat(workspace): CliPolicy desk-local command gate (deny>allow, default-deny allowlist)"
```

---

## Task 5: WorkspaceBackend Protocol (the swap seam)

**Files:**
- Create: `src/fleetlib/workspace/backend.py`
- Modify: `src/fleetlib/workspace/__init__.py`
- Test: `tests/test_backend_protocol.py`

- [ ] **Step 1: Write the failing test**

```python
# tests/test_backend_protocol.py
from fleetlib.workspace import ExecResult, Scope, WorkspaceBackend

SCOPE = Scope(tenant_id="acme", agent_id="planner")


class _Dummy:
    def root_for(self, scope: Scope) -> str:
        return "/tmp/x"

    def write_file(self, path: str, data: str, scope: Scope) -> None:
        return None

    def read_file(self, path: str, scope: Scope) -> str:
        return ""

    def list_files(self, scope: Scope) -> list[str]:
        return []

    def delete_file(self, path: str, scope: Scope) -> None:
        return None

    def exec(self, command: str, scope: Scope) -> ExecResult:
        return ExecResult(exit_code=0)


def test_protocol_is_runtime_checkable():
    assert isinstance(_Dummy(), WorkspaceBackend)


def test_incomplete_class_is_not_a_backend():
    class Partial:
        def read_file(self, path, scope):
            return ""

    assert not isinstance(Partial(), WorkspaceBackend)
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/test_backend_protocol.py -v`
Expected: FAIL with `ImportError: cannot import name 'WorkspaceBackend'`

- [ ] **Step 3: Write minimal implementation**

```python
# src/fleetlib/workspace/backend.py
"""WorkspaceBackend — the swappable persistence + exec primitive.

A backend is DUMB on purpose: it persists files and runs commands rooted at one desk, and
nothing more. All desk features (CLI policy, handoff, compact, manifest) live in the
Workspace facade above it, which is what keeps the backend swappable. Every method takes a
Scope; confinement to <root>/<tenant_id>/<agent_id> is part of the contract. The default is
LocalFilesystemBackend; Daytona/E2B/OpenHands are optional-extra stubs.
"""

from __future__ import annotations

from typing import Protocol, runtime_checkable

from fleetlib.workspace.models import ExecResult
from fleetlib.workspace.scope import Scope


@runtime_checkable
class WorkspaceBackend(Protocol):
    def root_for(self, scope: Scope) -> str:
        """Absolute path of the desk root for scope (created on demand)."""
        ...

    def write_file(self, path: str, data: str, scope: Scope) -> None:
        """Write data to path (relative to the desk root) within scope."""
        ...

    def read_file(self, path: str, scope: Scope) -> str:
        """Read path (relative to the desk root) within scope."""
        ...

    def list_files(self, scope: Scope) -> list[str]:
        """List relative file paths under the desk root for scope."""
        ...

    def delete_file(self, path: str, scope: Scope) -> None:
        """Delete path (relative to the desk root) within scope."""
        ...

    def exec(self, command: str, scope: Scope) -> ExecResult:
        """Run command with the desk root as cwd; return a typed ExecResult."""
        ...
```

```python
# src/fleetlib/workspace/__init__.py  (extend imports + __all__)
from fleetlib.workspace.backend import WorkspaceBackend
from fleetlib.workspace.models import CapabilityManifest, ExecResult
from fleetlib.workspace.policy import CliPolicy, PolicyError
from fleetlib.workspace.scope import Scope

__all__ = [
    "__version__",
    "Scope",
    "ExecResult",
    "CapabilityManifest",
    "CliPolicy",
    "PolicyError",
    "WorkspaceBackend",
]
```

- [ ] **Step 4: Run test to verify it passes**

Run: `pytest tests/test_backend_protocol.py -v`
Expected: PASS (2 passed)

- [ ] **Step 5: Commit**

```bash
git add src/fleetlib/workspace/backend.py src/fleetlib/workspace/__init__.py tests/test_backend_protocol.py
git commit -m "feat(workspace): WorkspaceBackend Protocol — the dumb, scope-first swap seam"
```

---

## Task 6: LocalFilesystemBackend — files + traversal confinement (default, part 1)

**Files:**
- Create: `src/fleetlib/workspace/local.py`
- Modify: `src/fleetlib/workspace/__init__.py`
- Test: `tests/test_local_files.py`

- [ ] **Step 1: Write the failing test**

```python
# tests/test_local_files.py
import pytest

from fleetlib.workspace import LocalFilesystemBackend, Scope

SCOPE = Scope(tenant_id="acme", agent_id="planner")


def test_write_read_roundtrip(tmp_path):
    be = LocalFilesystemBackend(base_dir=tmp_path)
    be.write_file("notes.md", "hello desk", SCOPE)
    assert be.read_file("notes.md", SCOPE) == "hello desk"


def test_write_creates_nested_dirs(tmp_path):
    be = LocalFilesystemBackend(base_dir=tmp_path)
    be.write_file("sub/dir/file.txt", "x", SCOPE)
    assert be.read_file("sub/dir/file.txt", SCOPE) == "x"


def test_list_and_delete(tmp_path):
    be = LocalFilesystemBackend(base_dir=tmp_path)
    be.write_file("a.txt", "1", SCOPE)
    be.write_file("b/c.txt", "2", SCOPE)
    assert set(be.list_files(SCOPE)) == {"a.txt", "b/c.txt"}
    be.delete_file("a.txt", SCOPE)
    assert set(be.list_files(SCOPE)) == {"b/c.txt"}


def test_root_is_under_tenant_agent(tmp_path):
    be = LocalFilesystemBackend(base_dir=tmp_path)
    root = be.root_for(SCOPE)
    assert root.endswith("acme/planner")


def test_path_traversal_is_confined(tmp_path):
    be = LocalFilesystemBackend(base_dir=tmp_path)
    with pytest.raises(ValueError, match="escapes desk root"):
        be.write_file("../../etc/passwd", "owned", SCOPE)
    with pytest.raises(ValueError, match="escapes desk root"):
        be.read_file("../secret", SCOPE)
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/test_local_files.py -v`
Expected: FAIL with `ImportError: cannot import name 'LocalFilesystemBackend'`

- [ ] **Step 3: Write minimal implementation**

```python
# src/fleetlib/workspace/local.py
"""LocalFilesystemBackend — the ONE working default backend.

A persistent directory per desk: <base_dir>/<tenant_id>/<agent_id>/. Files survive across
process restarts (persistent by default). Every relative path is resolved and checked to
stay inside the desk root — traversal (e.g. "../../etc/passwd") is rejected. This is the
opinionated default that works out of the box; advanced users swap in Daytona/E2B/OpenHands.
"""

from __future__ import annotations

import subprocess
from pathlib import Path

from fleetlib.workspace.models import ExecResult
from fleetlib.workspace.scope import Scope


class LocalFilesystemBackend:
    """Tenant/agent-isolated filesystem desk with traversal confinement."""

    def __init__(self, base_dir: str | Path = ".fleet-workspaces") -> None:
        self._base = Path(base_dir)

    def _root_path(self, scope: Scope) -> Path:
        root = (self._base / scope.tenant_id / scope.agent_id).resolve()
        root.mkdir(parents=True, exist_ok=True)
        return root

    def _resolve(self, path: str, scope: Scope) -> Path:
        root = self._root_path(scope)
        target = (root / path).resolve()
        if root != target and root not in target.parents:
            raise ValueError(f"path {path!r} escapes desk root")
        return target

    def root_for(self, scope: Scope) -> str:
        return str(self._root_path(scope))

    def write_file(self, path: str, data: str, scope: Scope) -> None:
        target = self._resolve(path, scope)
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(data, encoding="utf-8")

    def read_file(self, path: str, scope: Scope) -> str:
        return self._resolve(path, scope).read_text(encoding="utf-8")

    def list_files(self, scope: Scope) -> list[str]:
        root = self._root_path(scope)
        return sorted(
            str(p.relative_to(root)) for p in root.rglob("*") if p.is_file()
        )

    def delete_file(self, path: str, scope: Scope) -> None:
        self._resolve(path, scope).unlink(missing_ok=True)

    def exec(self, command: str, scope: Scope) -> ExecResult:  # implemented in Task 7
        raise NotImplementedError
```

```python
# src/fleetlib/workspace/__init__.py  (extend imports + __all__)
from fleetlib.workspace.backend import WorkspaceBackend
from fleetlib.workspace.local import LocalFilesystemBackend
from fleetlib.workspace.models import CapabilityManifest, ExecResult
from fleetlib.workspace.policy import CliPolicy, PolicyError
from fleetlib.workspace.scope import Scope

__all__ = [
    "__version__",
    "Scope",
    "ExecResult",
    "CapabilityManifest",
    "CliPolicy",
    "PolicyError",
    "WorkspaceBackend",
    "LocalFilesystemBackend",
]
```

- [ ] **Step 4: Run test to verify it passes**

Run: `pytest tests/test_local_files.py -v`
Expected: PASS (5 passed)

- [ ] **Step 5: Commit**

```bash
git add src/fleetlib/workspace/local.py src/fleetlib/workspace/__init__.py tests/test_local_files.py
git commit -m "feat(workspace): LocalFilesystemBackend files + path-traversal confinement"
```

---

## Task 7: LocalFilesystemBackend — exec rooted at the desk (default, part 2)

**Files:**
- Modify: `src/fleetlib/workspace/local.py`
- Test: `tests/test_local_exec.py`

- [ ] **Step 1: Write the failing test**

```python
# tests/test_local_exec.py
from fleetlib.workspace import ExecResult, LocalFilesystemBackend, Scope

SCOPE = Scope(tenant_id="acme", agent_id="planner")


def test_exec_returns_exec_result(tmp_path):
    be = LocalFilesystemBackend(base_dir=tmp_path)
    res = be.exec("echo hello", SCOPE)
    assert isinstance(res, ExecResult)
    assert res.exit_code == 0
    assert "hello" in res.stdout


def test_exec_runs_with_desk_as_cwd(tmp_path):
    be = LocalFilesystemBackend(base_dir=tmp_path)
    be.write_file("marker.txt", "present", SCOPE)
    res = be.exec("ls", SCOPE)
    assert "marker.txt" in res.stdout


def test_exec_captures_nonzero_exit_and_stderr(tmp_path):
    be = LocalFilesystemBackend(base_dir=tmp_path)
    res = be.exec("ls /no/such/path/xyz", SCOPE)
    assert res.exit_code != 0
    assert res.ok is False
    assert res.stderr != ""
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/test_local_exec.py -v`
Expected: FAIL with `NotImplementedError`

- [ ] **Step 3: Write minimal implementation**

```python
# src/fleetlib/workspace/local.py  — replace the exec() stub with:

    def exec(self, command: str, scope: Scope) -> ExecResult:
        root = self._root_path(scope)
        completed = subprocess.run(
            command,
            shell=True,
            cwd=str(root),
            capture_output=True,
            text=True,
        )
        return ExecResult(
            exit_code=completed.returncode,
            stdout=completed.stdout,
            stderr=completed.stderr,
        )
```

- [ ] **Step 4: Run test to verify it passes**

Run: `pytest tests/test_local_exec.py -v`
Expected: PASS (3 passed)

- [ ] **Step 5: Commit**

```bash
git add src/fleetlib/workspace/local.py tests/test_local_exec.py
git commit -m "feat(workspace): LocalFilesystemBackend exec rooted at the desk -> ExecResult"
```

---

## Task 8: Tenant + agent isolation is real

**Files:**
- Test: `tests/test_isolation.py`

(No implementation — this proves the per-scope root already isolates. If it fails, the bug is real.)

- [ ] **Step 1: Write the failing test**

```python
# tests/test_isolation.py
from fleetlib.workspace import LocalFilesystemBackend, Scope

ACME_A = Scope(tenant_id="acme", agent_id="planner")
ACME_B = Scope(tenant_id="acme", agent_id="builder")
GLOBEX_A = Scope(tenant_id="globex", agent_id="planner")


def test_agents_in_same_tenant_are_isolated(tmp_path):
    be = LocalFilesystemBackend(base_dir=tmp_path)
    be.write_file("note.md", "planner only", ACME_A)
    assert be.list_files(ACME_B) == []


def test_tenants_are_isolated(tmp_path):
    be = LocalFilesystemBackend(base_dir=tmp_path)
    be.write_file("note.md", "acme planner", ACME_A)
    be.write_file("note.md", "globex planner", GLOBEX_A)
    assert be.read_file("note.md", ACME_A) == "acme planner"
    assert be.read_file("note.md", GLOBEX_A) == "globex planner"
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/test_isolation.py -v`
Expected: PASS immediately (isolation is structural via the per-scope root). If it FAILS, fix `_root_path` keying before proceeding.

- [ ] **Step 3: No implementation needed**

Isolation is enforced by the `<tenant_id>/<agent_id>` root in `LocalFilesystemBackend`. This task locks it with a regression test.

- [ ] **Step 4: Run test to confirm green**

Run: `pytest tests/test_isolation.py -v`
Expected: PASS (2 passed)

- [ ] **Step 5: Commit**

```bash
git add tests/test_isolation.py
git commit -m "test(workspace): lock tenant + agent desk isolation as a regression guard"
```

---

## Task 9: Workspace facade — write / read / run (policy) + manifest

**Files:**
- Create: `src/fleetlib/workspace/desk.py`
- Modify: `src/fleetlib/workspace/__init__.py`
- Test: `tests/test_desk.py`

- [ ] **Step 1: Write the failing test**

```python
# tests/test_desk.py
import pytest

from fleetlib.workspace import (
    CapabilityManifest,
    CliPolicy,
    LocalFilesystemBackend,
    PolicyError,
    Scope,
    Workspace,
)

SCOPE = Scope(tenant_id="acme", agent_id="planner")


def _ws(tmp_path, **kw):
    return Workspace(backend=LocalFilesystemBackend(base_dir=tmp_path), scope=SCOPE, **kw)


def test_write_and_read(tmp_path):
    ws = _ws(tmp_path)
    ws.write("notes.md", "first day")
    assert ws.read("notes.md") == "first day"


def test_run_returns_exec_result(tmp_path):
    ws = _ws(tmp_path)
    res = ws.run("echo hi")
    assert res.exit_code == 0
    assert "hi" in res.stdout


def test_run_enforces_policy_before_exec(tmp_path):
    ws = _ws(tmp_path, policy=CliPolicy(deny=["rm"]))
    # If policy let it through, this file would be deleted; assert it is NOT reached.
    ws.write("keep.txt", "safe")
    with pytest.raises(PolicyError, match="rm"):
        ws.run("rm keep.txt")
    assert ws.read("keep.txt") == "safe"


def test_manifest_round_trip_is_stored_not_mounted(tmp_path):
    ws = _ws(tmp_path)
    assert ws.manifest().refs == []
    ws.set_manifest(CapabilityManifest(refs=["mcp://gateway/call_tool"]))
    assert ws.manifest().refs == ["mcp://gateway/call_tool"]
    # Boundary: the facade STORES the manifest; it never mounts capabilities.
    assert not hasattr(ws, "mount")
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/test_desk.py -v`
Expected: FAIL with `ImportError: cannot import name 'Workspace'`

- [ ] **Step 3: Write minimal implementation**

```python
# src/fleetlib/workspace/desk.py
"""Workspace — the agent desk facade.

Thin control layer over a WorkspaceBackend + a Scope. It adds the charter's value-add ON
TOP of raw persistence: scoped write/read, run() that enforces CliPolicy BEFORE delegating
to backend.exec, a handoff/day-note, rule-based auto-compact, and storage for a passive
CapabilityManifest. It does NOT mount MCP capabilities (agent runtime's job) and does NOT
own hierarchy/policy (organization's job). Persistent by default.
"""

from __future__ import annotations

import json

from fleetlib.workspace.backend import WorkspaceBackend
from fleetlib.workspace.models import CapabilityManifest, ExecResult
from fleetlib.workspace.policy import CliPolicy
from fleetlib.workspace.scope import Scope

_MANIFEST_FILE = ".workspace/manifest.json"


class Workspace:
    """The agent's persistent desk."""

    def __init__(
        self,
        *,
        backend: WorkspaceBackend,
        scope: Scope,
        policy: CliPolicy | None = None,
    ) -> None:
        self._backend = backend
        self._scope = scope
        self._policy = policy or CliPolicy()

    @property
    def scope(self) -> Scope:
        return self._scope

    def write(self, path: str, data: str) -> None:
        self._backend.write_file(path, data, self._scope)

    def read(self, path: str) -> str:
        return self._backend.read_file(path, self._scope)

    def list(self) -> list[str]:
        return self._backend.list_files(self._scope)

    def run(self, command: str) -> ExecResult:
        self._policy.check(command)  # raises PolicyError before exec is reached
        return self._backend.exec(command, self._scope)

    def set_manifest(self, manifest: CapabilityManifest) -> None:
        self._backend.write_file(_MANIFEST_FILE, manifest.model_dump_json(), self._scope)

    def manifest(self) -> CapabilityManifest:
        try:
            raw = self._backend.read_file(_MANIFEST_FILE, self._scope)
        except (FileNotFoundError, ValueError):
            return CapabilityManifest()
        return CapabilityManifest(**json.loads(raw))
```

```python
# src/fleetlib/workspace/__init__.py  (extend imports + __all__)
from fleetlib.workspace.backend import WorkspaceBackend
from fleetlib.workspace.desk import Workspace
from fleetlib.workspace.local import LocalFilesystemBackend
from fleetlib.workspace.models import CapabilityManifest, ExecResult
from fleetlib.workspace.policy import CliPolicy, PolicyError
from fleetlib.workspace.scope import Scope

__all__ = [
    "__version__",
    "Scope",
    "ExecResult",
    "CapabilityManifest",
    "CliPolicy",
    "PolicyError",
    "WorkspaceBackend",
    "LocalFilesystemBackend",
    "Workspace",
]
```

- [ ] **Step 4: Run test to verify it passes**

Run: `pytest tests/test_desk.py -v`
Expected: PASS (4 passed)

- [ ] **Step 5: Commit**

```bash
git add src/fleetlib/workspace/desk.py src/fleetlib/workspace/__init__.py tests/test_desk.py
git commit -m "feat(workspace): Workspace facade — write/read/run(policy) + manifest store"
```

---

## Task 10: Handoff / day-note + rule-based auto-compact

**Files:**
- Modify: `src/fleetlib/workspace/desk.py`
- Test: `tests/test_handoff_compact.py`

- [ ] **Step 1: Write the failing test**

```python
# tests/test_handoff_compact.py
from fleetlib.workspace import LocalFilesystemBackend, Scope, Workspace

SCOPE = Scope(tenant_id="acme", agent_id="planner")


def _ws(tmp_path):
    return Workspace(backend=LocalFilesystemBackend(base_dir=tmp_path), scope=SCOPE)


def test_handoff_appends_entries(tmp_path):
    ws = _ws(tmp_path)
    ws.handoff("tomorrow: finish the deploy")
    ws.handoff("also: rotate the cert")
    note = ws.day_note()
    assert "finish the deploy" in note
    assert "rotate the cert" in note


def test_handoff_persists_to_a_file(tmp_path):
    ws = _ws(tmp_path)
    ws.handoff("pick up here")
    assert "HANDOFF.md" in ws.list()


def test_compact_caps_entries_by_rule_keeping_newest(tmp_path):
    ws = _ws(tmp_path)
    for i in range(10):
        ws.handoff(f"entry {i}")
    dropped = ws.compact(max_entries=3)
    note = ws.day_note()
    assert dropped == 7
    assert "entry 9" in note
    assert "entry 0" not in note
    assert note.count("entry ") == 3


def test_compact_noop_when_under_limit(tmp_path):
    ws = _ws(tmp_path)
    ws.handoff("only one")
    assert ws.compact(max_entries=5) == 0
    assert "only one" in ws.day_note()
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/test_handoff_compact.py -v`
Expected: FAIL with `AttributeError: 'Workspace' object has no attribute 'handoff'`

- [ ] **Step 3: Write minimal implementation**

```python
# src/fleetlib/workspace/desk.py  — add module constant near _MANIFEST_FILE:
_HANDOFF_FILE = "HANDOFF.md"

# src/fleetlib/workspace/desk.py  — add these methods to Workspace:

    def _read_handoff_entries(self) -> list[str]:
        try:
            raw = self._backend.read_file(_HANDOFF_FILE, self._scope)
        except (FileNotFoundError, ValueError):
            return []
        return [line for line in raw.splitlines() if line.strip()]

    def handoff(self, note: str) -> None:
        """Append a day-note line so the next session picks up where this one left off."""
        entries = self._read_handoff_entries()
        entries.append(f"- {note}")
        self._backend.write_file(_HANDOFF_FILE, "\n".join(entries) + "\n", self._scope)

    def day_note(self) -> str:
        """The current handoff/day-note text."""
        try:
            return self._backend.read_file(_HANDOFF_FILE, self._scope)
        except (FileNotFoundError, ValueError):
            return ""

    def compact(self, *, max_entries: int = 50) -> int:
        """Auto-compact: keep only the newest max_entries handoff lines. Rule-based, no LLM.

        Returns the number of entries dropped. Compaction is deterministic (a count cap),
        not summarization — workspace has no model and depends only on pydantic.
        """
        entries = self._read_handoff_entries()
        if len(entries) <= max_entries:
            return 0
        kept = entries[-max_entries:]
        dropped = len(entries) - len(kept)
        self._backend.write_file(_HANDOFF_FILE, "\n".join(kept) + "\n", self._scope)
        return dropped
```

- [ ] **Step 4: Run test to verify it passes**

Run: `pytest tests/test_handoff_compact.py -v`
Expected: PASS (4 passed)

- [ ] **Step 5: Commit**

```bash
git add src/fleetlib/workspace/desk.py tests/test_handoff_compact.py
git commit -m "feat(workspace): handoff/day-note + rule-based auto-compact (no LLM)"
```

---

## Task 11: Persistence by default + ephemeral mode + open_workspace()

**Files:**
- Modify: `src/fleetlib/workspace/desk.py`
- Modify: `src/fleetlib/workspace/__init__.py`
- Test: `tests/test_persistence.py`

- [ ] **Step 1: Write the failing test**

```python
# tests/test_persistence.py
from fleetlib.workspace import Scope, open_workspace

SCOPE = Scope(tenant_id="acme", agent_id="planner")


def test_files_persist_across_instances(tmp_path):
    ws1 = open_workspace(scope=SCOPE, base_dir=tmp_path)
    ws1.write("notes.md", "kept between sessions")
    ws1.handoff("resume the migration")

    # A brand-new Workspace over the same scope/dir is a "next session".
    ws2 = open_workspace(scope=SCOPE, base_dir=tmp_path)
    assert ws2.read("notes.md") == "kept between sessions"
    assert "resume the migration" in ws2.day_note()


def test_ephemeral_mode_does_not_persist():
    ws = open_workspace(scope=SCOPE, ephemeral=True)
    ws.write("scratch.txt", "temporary")
    root = ws.root
    ws.close()

    import os

    assert not os.path.exists(root)  # ephemeral desk is cleaned up on close


def test_open_workspace_defaults_to_persistent(tmp_path):
    ws = open_workspace(scope=SCOPE, base_dir=tmp_path)
    ws.write("a.txt", "1")
    ws.close()
    import os

    assert os.path.exists(ws.root)  # persistent desk survives close
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/test_persistence.py -v`
Expected: FAIL with `ImportError: cannot import name 'open_workspace'`

- [ ] **Step 3: Write minimal implementation**

```python
# src/fleetlib/workspace/desk.py  — add at top of imports:
import shutil
import tempfile
from pathlib import Path  # for the open_workspace() base_dir type

# src/fleetlib/workspace/desk.py  — add to Workspace.__init__ signature + body:
#   add parameter `ephemeral: bool = False` after policy,
#   and store `self._ephemeral = ephemeral`
#   (full updated __init__ shown below for clarity)

    def __init__(
        self,
        *,
        backend: WorkspaceBackend,
        scope: Scope,
        policy: CliPolicy | None = None,
        ephemeral: bool = False,
    ) -> None:
        self._backend = backend
        self._scope = scope
        self._policy = policy or CliPolicy()
        self._ephemeral = ephemeral

    @property
    def root(self) -> str:
        """Absolute path of this desk's root."""
        return self._backend.root_for(self._scope)

    def close(self) -> None:
        """Release the desk. Ephemeral desks are deleted; persistent ones are left intact."""
        if self._ephemeral:
            shutil.rmtree(self.root, ignore_errors=True)


# src/fleetlib/workspace/desk.py  — append the factory at module level:

def open_workspace(
    *,
    scope: Scope,
    base_dir: str | Path | None = None,
    policy: CliPolicy | None = None,
    ephemeral: bool = False,
) -> Workspace:
    """Open the default (LocalFilesystem) desk for scope.

    Persistent by default: files live under base_dir/<tenant>/<agent> across sessions.
    ephemeral=True uses a throwaway temp dir cleaned up on close().
    """
    from fleetlib.workspace.local import LocalFilesystemBackend

    if ephemeral:
        base = tempfile.mkdtemp(prefix="fleet-ws-ephemeral-")
    else:
        base = base_dir or ".fleet-workspaces"
    backend = LocalFilesystemBackend(base_dir=base)
    return Workspace(backend=backend, scope=scope, policy=policy, ephemeral=ephemeral)
```

```python
# src/fleetlib/workspace/__init__.py  (ADDITIVE — keep all earlier re-exports from
# Tasks 2–9; only the desk import line changes to add open_workspace)
from fleetlib.workspace.desk import Workspace, open_workspace

__all__ = [
    "__version__",
    "Scope",
    "ExecResult",
    "CapabilityManifest",
    "CliPolicy",
    "PolicyError",
    "WorkspaceBackend",
    "LocalFilesystemBackend",
    "Workspace",
    "open_workspace",
]
```

- [ ] **Step 4: Run test to verify it passes**

Run: `pytest tests/test_persistence.py -v`
Expected: PASS (3 passed)

- [ ] **Step 5: Commit**

```bash
git add src/fleetlib/workspace/desk.py src/fleetlib/workspace/__init__.py tests/test_persistence.py
git commit -m "feat(workspace): persistent-by-default + ephemeral mode + open_workspace()"
```

---

## Task 12: Optional-extra backend stubs (SPI demonstration, raise on use)

**Files:**
- Create: `src/fleetlib/workspace/adapters/__init__.py`
- Create: `src/fleetlib/workspace/adapters/_stub.py`
- Create: `src/fleetlib/workspace/adapters/daytona.py`
- Create: `src/fleetlib/workspace/adapters/e2b.py`
- Create: `src/fleetlib/workspace/adapters/openhands.py`
- Test: `tests/test_adapter_stubs.py`

- [ ] **Step 1: Write the failing test**

```python
# tests/test_adapter_stubs.py
import pytest

from fleetlib.workspace.adapters._stub import MissingExtraError
from fleetlib.workspace.adapters.daytona import DaytonaBackend
from fleetlib.workspace.adapters.e2b import E2BBackend
from fleetlib.workspace.adapters.openhands import OpenHandsBackend


@pytest.mark.parametrize(
    "cls,extra",
    [
        (DaytonaBackend, "daytona"),
        (E2BBackend, "e2b"),
        (OpenHandsBackend, "openhands"),
    ],
)
def test_stub_instantiation_raises_until_extra_and_impl_land(cls, extra):
    # Stubs import fine WITHOUT the extra (no real SDK imported at module top),
    # but instantiating one tells you exactly which extra to install.
    with pytest.raises(MissingExtraError, match=extra):
        cls()
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/test_adapter_stubs.py -v`
Expected: FAIL with `ModuleNotFoundError: No module named 'fleetlib.workspace.adapters'`

- [ ] **Step 3: Write minimal implementation**

```python
# src/fleetlib/workspace/adapters/__init__.py
"""Optional-extra backend adapters. Stubs today — each names the WorkspaceBackend it will
become and raises MissingExtraError until its extra (and a real impl) land. Stubs do NOT
import the real SDK at module top, so they import fine without the extra installed."""
```

```python
# src/fleetlib/workspace/adapters/_stub.py
"""Shared helper for optional-extra adapter stubs."""

from __future__ import annotations


class MissingExtraError(RuntimeError):
    """Raised when an optional-extra backend is used before its extra/impl exist."""


def require_extra(extra: str) -> None:
    raise MissingExtraError(
        f"backend requires the optional '{extra}' extra and a real implementation; "
        f"install with: pip install fleetlib-workspace[{extra}] (stub not yet implemented)"
    )
```

```python
# src/fleetlib/workspace/adapters/daytona.py
"""Daytona adapter — STUB. Persistent sandboxes + snapshots; raises until the daytona extra."""

from __future__ import annotations

from fleetlib.workspace.adapters._stub import require_extra


class DaytonaBackend:
    def __init__(self, *args, **kwargs) -> None:
        require_extra("daytona")
```

```python
# src/fleetlib/workspace/adapters/e2b.py
"""E2B adapter — STUB. Pause/resume fs + process; raises until the e2b extra."""

from __future__ import annotations

from fleetlib.workspace.adapters._stub import require_extra


class E2BBackend:
    def __init__(self, *args, **kwargs) -> None:
        require_extra("e2b")
```

```python
# src/fleetlib/workspace/adapters/openhands.py
"""OpenHands adapter — STUB. Persists conversation + tools + agent state; raises until the openhands extra."""

from __future__ import annotations

from fleetlib.workspace.adapters._stub import require_extra


class OpenHandsBackend:
    def __init__(self, *args, **kwargs) -> None:
        require_extra("openhands")
```

- [ ] **Step 4: Run test to verify it passes**

Run: `pytest tests/test_adapter_stubs.py -v`
Expected: PASS (3 passed)

- [ ] **Step 5: Commit**

```bash
git add src/fleetlib/workspace/adapters tests/test_adapter_stubs.py
git commit -m "feat(workspace): daytona/e2b/openhands adapter stubs (raise on use)"
```

---

## Task 13: Full-suite green + public API lock

**Files:**
- Test: `tests/test_public_api.py`

- [ ] **Step 1: Write the failing test**

```python
# tests/test_public_api.py
import fleetlib.workspace as w


def test_public_surface_is_complete():
    expected = {
        "__version__",
        "Scope",
        "ExecResult",
        "CapabilityManifest",
        "CliPolicy",
        "PolicyError",
        "WorkspaceBackend",
        "LocalFilesystemBackend",
        "Workspace",
        "open_workspace",
    }
    assert expected <= set(w.__all__)
    for name in expected:
        assert hasattr(w, name), name


def test_end_to_end_open_write_run_handoff(tmp_path):
    scope = w.Scope(tenant_id="acme", agent_id="planner")
    ws = w.open_workspace(scope=scope, base_dir=tmp_path, policy=w.CliPolicy(deny=["rm"]))

    ws.write("plan.md", "step 1: provision")
    assert ws.read("plan.md") == "step 1: provision"

    res = ws.run("echo working")
    assert res.ok and "working" in res.stdout

    ws.set_manifest(w.CapabilityManifest(refs=["mcp://gateway/call_tool"]))
    ws.handoff("next: run step 2")

    # A fresh session over the same scope resumes the desk.
    ws2 = w.open_workspace(scope=scope, base_dir=tmp_path)
    assert ws2.read("plan.md") == "step 1: provision"
    assert ws2.manifest().refs == ["mcp://gateway/call_tool"]
    assert "run step 2" in ws2.day_note()
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/test_public_api.py -v`
Expected: FAIL (file/test not yet present) — becomes PASS once added, since the API already exists from prior tasks.

- [ ] **Step 3: No new implementation**

The public API was assembled incrementally in Tasks 1–12. This task only adds the end-to-end + surface-lock test.

- [ ] **Step 4: Run the full suite**

Run: `pytest -v`
Expected: PASS (all tests across all files green)

- [ ] **Step 5: Commit**

```bash
git add tests/test_public_api.py
git commit -m "test(workspace): lock public API surface + end-to-end open/write/run/handoff"
```

---

## Self-Review Checklist (run after implementing)

1. **Charter coverage** — persistent files (`write`/`read`, Task 9 + persistence Task 11); CLI policy (`run` gated by `CliPolicy`, Tasks 4/9); handoff/day-note (Task 10); auto-compact (Task 10, rule-based); capability MANIFEST stored as a reference (Tasks 3/9); persistent by default + ephemeral mode (Task 11); per-agent/tenant scope (Task 2, isolation Task 8). ✔
2. **Principles** — THIN: backend is a dumb files+exec primitive, facade is the only value-add; no sandbox provider re-implemented (Tasks 5–7). Protocol + ONE working default (`LocalFilesystemBackend`) + stubs (Tasks 5/6/7/12). Scope on every call; isolation proven on a real filesystem incl. traversal confinement (Tasks 6/8). Opinionated default works out of the box (`open_workspace`, Tasks 11/13). ✔
3. **Boundaries (load-bearing)** — MCP mounting NOT done here: `CapabilityManifest` is passive data, facade has no `mount()` (`test_manifest_is_passive_data_only`, `test_manifest_round_trip_is_stored_not_mounted`). Org policy NOT done here: `CliPolicy` is desk-local commands only, no roles/escalation (Task 4 docstring + tests). auto-compact is rule-based, no LLM / no lib-ai import (Task 10). Runtime dep is `pydantic` only — sibling lib depends on nothing else. ✔
4. **Packaging** — PEP 420 namespace (no `src/fleetlib/__init__.py`, Task 1 test asserts it), src layout, `py.typed`, hatchling, optional extras `daytona`/`e2b`/`openhands`/`dev`; stubs import without the extra (`test_adapter_stubs`). ✔
5. **Type consistency** — `Scope(tenant_id, agent_id).key`, `ExecResult.ok`, `CliPolicy.check`/`PolicyError`, `WorkspaceBackend` (root_for/write_file/read_file/list_files/delete_file/exec), `Workspace` (write/read/run/handoff/day_note/compact/set_manifest/manifest/root/close), `open_workspace(scope=…, base_dir=…, ephemeral=…)` used identically across tasks. ✔
