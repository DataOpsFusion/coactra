# coactra.memory Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Ship a publishable, backend-neutral memory **connector** — `learn(events, scope)` / `recall(query, scope, capabilities=...)` / `export(scope, to=adapter)` — over a `MemoryBackend` Protocol, with one working in-process default adapter and a lossy-but-honest export (capability negotiation + provenance + explicit unsupported-feature report).

**Architecture:** A thin SPI, not an engine. A `MemoryBackend` `typing.Protocol` defines the contract; the ONE working default (`InProcessBackend`) is a tenant-scoped, pydantic-only store with lexical recall. `export()` moves items between two backends by intersecting their declared `Capability` sets — anything the target can't represent is **dropped/degraded and reported**, never silently lost and never claimed lossless. mem0 / graphiti / letta are optional-extra adapter **stubs** that demonstrate the SPI and raise on use. The charter states the contract as `export(to=adapter)`; this plan realizes it as a free function `export(source, target, *, scope)` — semantically the same "move learning into another backend" operation, made explicit about which backend is the source and keeping the lossy negotiation in one place. `Scope` (tenant + namespace) is a mandatory argument on every call; isolation is enforced in the default store, not assumed.

**Tech Stack:** Python 3.12+, pydantic v2, hatchling (PEP 420 namespace package, src layout), pytest. Optional extras: `mem0ai`, `graphiti-core`, `letta` (stubs only). Memory learns from **conversation** (summaries/lessons) — distinct from lib-ai reasoning-capture; no shared store.

---

## File Structure

| File | Responsibility |
|------|----------------|
| `pyproject.toml` | Distribution `coactra-memory`; hatchling targets the `coactra` namespace dir; runtime dep `pydantic`; `[project.optional-dependencies]` for `mem0`/`graphiti`/`letta`/`dev`. |
| `src/coactra/memory/__init__.py` | Public API surface — re-exports `Scope`, `MemoryEvent`, `MemoryItem`, `Provenance`, `Capability`, `MemoryBackend`, `InProcessBackend`, `ExportReport`, `export`. NO `src/coactra/__init__.py` (namespace package). |
| `src/coactra/memory/py.typed` | PEP 561 typing marker. |
| `src/coactra/memory/scope.py` | `Scope` value object — `tenant_id` + `namespace`; the multi-tenant key threaded through every call. |
| `src/coactra/memory/models.py` | `Provenance`, `MemoryEvent` (input), `MemoryItem` (stored, carries provenance + capabilities-it-uses). |
| `src/coactra/memory/capabilities.py` | `Capability` enum — the ONE vocabulary shared by `export` AND `recall`. |
| `src/coactra/memory/backend.py` | `MemoryBackend` `typing.Protocol` — `capabilities()`, `learn()`, `recall()`, `dump()`, `ingest()`. |
| `src/coactra/memory/inprocess.py` | `InProcessBackend` — the ONE working default: tenant-isolated dict store, trivial dedup, lexical recall. |
| `src/coactra/memory/export.py` | `ExportReport` + `export()` — capability negotiation, provenance preservation, explicit dropped/degraded-feature report. |
| `src/coactra/memory/adapters/__init__.py` | Adapters subpackage marker. |
| `src/coactra/memory/adapters/_stub.py` | `MissingExtraError` + `require_extra()` helper for optional-extra import guards. |
| `src/coactra/memory/adapters/mem0.py` | `Mem0Backend` stub — declares its `Capability` set; raises `MissingExtraError` until the `mem0` extra + real impl land. |
| `src/coactra/memory/adapters/graphiti.py` | `GraphitiBackend` stub — graph capabilities; raises until `graphiti` extra. |
| `src/coactra/memory/adapters/letta.py` | `LettaBackend` stub — memory-block capabilities; raises until `letta` extra. |
| `tests/test_packaging.py` | Asserts `import coactra.memory` works and `coactra` is a PEP 420 namespace package. |
| `tests/test_scope.py` | `Scope` equality/hashing/validation. |
| `tests/test_models.py` | Event→item, provenance always present. |
| `tests/test_capabilities.py` | Vocabulary stability + set algebra. |
| `tests/test_inprocess.py` | Default backend: learn, dedup, lexical recall, capability-shaped recall. |
| `tests/test_isolation.py` | Tenant A cannot read tenant B's items. |
| `tests/test_export.py` | Lossy export reports drops on graph→vector; round-trip same-capability is total; provenance preserved. |
| `tests/test_adapter_stubs.py` | Stubs declare capabilities without the extra but raise `MissingExtraError` on instantiation/use. |

---

## Task 1: Package scaffold (namespace package + importable)

**Files:**
- Create: `pyproject.toml`
- Create: `src/coactra/memory/__init__.py`
- Create: `src/coactra/memory/py.typed`
- Test: `tests/test_packaging.py`

- [ ] **Step 1: Write the failing test**

```python
# tests/test_packaging.py
import importlib


def test_memory_imports():
    mod = importlib.import_module("coactra.memory")
    assert mod is not None


def test_coactra_is_namespace_package():
    import coactra

    # PEP 420 namespace packages have no __file__ and an empty/virtual __path__ entry list.
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
name = "coactra-memory"
version = "0.1.0"
description = "Backend-neutral memory connector SPI for AI agent fleets (learn / recall / lossy export)."
readme = "README.md"
requires-python = ">=3.12"
license = { text = "MIT" }
dependencies = ["pydantic>=2.7"]

[project.optional-dependencies]
mem0 = ["mem0ai>=0.1"]
graphiti = ["graphiti-core>=0.3"]
letta = ["letta>=0.5"]
dev = ["pytest>=8"]

[tool.hatch.build.targets.wheel]
# PEP 420 namespace: ship the coactra/ dir WITHOUT a top-level coactra/__init__.py
packages = ["src/coactra"]

[tool.hatch.build.targets.sdist]
include = ["src/coactra", "README.md", "tests"]
```

```python
# src/coactra/memory/__init__.py
"""coactra.memory — backend-neutral memory connector SPI.

Learns from CONVERSATION (summaries / lessons), recalls later, and exports learning
into any memory/RAG backend. export() is LOSSY by design: it negotiates capabilities,
preserves provenance, and reports every dropped or degraded feature. It never promises
lossless conversion.
"""

__all__ = [
    "__version__",
]

__version__ = "0.1.0"
```

```text
# src/coactra/memory/py.typed
```

(Do NOT create `src/coactra/__init__.py` — its absence is what makes `coactra` a namespace package.)

- [ ] **Step 4: Run test to verify it passes**

Run: `pip install -e . && pytest tests/test_packaging.py -v`
Expected: PASS (2 passed)

- [ ] **Step 5: Commit**

```bash
git add pyproject.toml src/coactra/memory/__init__.py src/coactra/memory/py.typed tests/test_packaging.py
git commit -m "feat(memory): namespace package scaffold + importable surface"
```

---

## Task 2: Scope — the mandatory multi-tenant key

**Files:**
- Create: `src/coactra/memory/scope.py`
- Modify: `src/coactra/memory/__init__.py`
- Test: `tests/test_scope.py`

- [ ] **Step 1: Write the failing test**

```python
# tests/test_scope.py
import pytest
from pydantic import ValidationError

from coactra.memory import Scope


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
# src/coactra/memory/scope.py
"""Scope — the tenant-scoped key threaded through every memory call.

Isolation is first-class: nothing crosses a (tenant_id, namespace) boundary unless an
explicit export moves it. namespace lets one tenant partition memory (per-agent,
per-session, shared) without leaking across tenants.
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
# src/coactra/memory/__init__.py  (append to __all__ and add import)
from coactra.memory.scope import Scope

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
git add src/coactra/memory/scope.py src/coactra/memory/__init__.py tests/test_scope.py
git commit -m "feat(memory): Scope — mandatory multi-tenant key (tenant_id + namespace)"
```

---

## Task 3: Models — events, items, provenance

**Files:**
- Create: `src/coactra/memory/models.py`
- Modify: `src/coactra/memory/__init__.py`
- Test: `tests/test_models.py`

- [ ] **Step 1: Write the failing test**

```python
# tests/test_models.py
from datetime import datetime, timezone

from coactra.memory import MemoryEvent, MemoryItem, Provenance


def test_event_minimal():
    e = MemoryEvent(content="user prefers dark mode")
    assert e.content == "user prefers dark mode"
    assert e.kind == "lesson"


def test_item_from_event_carries_provenance():
    e = MemoryEvent(content="deploy succeeded on attempt 2", kind="summary")
    item = MemoryItem.from_event(e, source_backend="inprocess")
    assert item.content == "deploy succeeded on attempt 2"
    assert item.kind == "summary"
    assert isinstance(item.id, str) and item.id
    assert isinstance(item.provenance, Provenance)
    assert item.provenance.source_backend == "inprocess"
    assert isinstance(item.provenance.created_at, datetime)
    assert item.provenance.created_at.tzinfo is timezone.utc


def test_item_provenance_is_never_optional():
    # MemoryItem MUST be constructed with provenance — there is no silent default.
    assert "provenance" in MemoryItem.model_fields
    assert MemoryItem.model_fields["provenance"].is_required()
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/test_models.py -v`
Expected: FAIL with `ImportError: cannot import name 'MemoryEvent'`

- [ ] **Step 3: Write minimal implementation**

```python
# src/coactra/memory/models.py
"""Memory data models.

MemoryEvent  — raw input ("what happened / what was learned" in a conversation).
MemoryItem   — a stored unit, always carrying Provenance (origin + lineage).
Provenance   — where an item came from; preserved across export so lineage survives
               a lossy backend hop.
"""

from __future__ import annotations

import uuid
from datetime import datetime, timezone
from typing import Literal

from pydantic import BaseModel, Field

MemoryKind = Literal["lesson", "summary", "fact", "preference"]


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


class Provenance(BaseModel):
    """Lineage of a MemoryItem. Set at creation, carried through every export hop."""

    source_backend: str
    created_at: datetime = Field(default_factory=_utcnow)
    exported_from: str | None = None  # backend name an item was exported out of, if any


class MemoryEvent(BaseModel):
    """A learnable conversational event handed to learn()."""

    content: str = Field(min_length=1)
    kind: MemoryKind = "lesson"
    tags: list[str] = Field(default_factory=list)


class MemoryItem(BaseModel):
    """A stored memory unit. Provenance is mandatory — there is no item without lineage."""

    id: str = Field(default_factory=lambda: uuid.uuid4().hex)
    content: str
    kind: MemoryKind
    tags: list[str] = Field(default_factory=list)
    provenance: Provenance

    @classmethod
    def from_event(cls, event: MemoryEvent, *, source_backend: str) -> "MemoryItem":
        return cls(
            content=event.content,
            kind=event.kind,
            tags=list(event.tags),
            provenance=Provenance(source_backend=source_backend),
        )
```

```python
# src/coactra/memory/__init__.py  (extend imports + __all__)
from coactra.memory.models import MemoryEvent, MemoryItem, Provenance
from coactra.memory.scope import Scope

__all__ = [
    "__version__",
    "Scope",
    "MemoryEvent",
    "MemoryItem",
    "Provenance",
]
```

- [ ] **Step 4: Run test to verify it passes**

Run: `pytest tests/test_models.py -v`
Expected: PASS (3 passed)

- [ ] **Step 5: Commit**

```bash
git add src/coactra/memory/models.py src/coactra/memory/__init__.py tests/test_models.py
git commit -m "feat(memory): MemoryEvent/MemoryItem/Provenance — items always carry lineage"
```

---

## Task 4: Capability vocabulary (shared by export AND recall)

**Files:**
- Create: `src/coactra/memory/capabilities.py`
- Modify: `src/coactra/memory/__init__.py`
- Test: `tests/test_capabilities.py`

- [ ] **Step 1: Write the failing test**

```python
# tests/test_capabilities.py
from coactra.memory import Capability


def test_vocabulary_is_stable():
    # Stability matters: adapters and exports negotiate against these exact names.
    names = {c.name for c in Capability}
    assert names == {
        "STORE",
        "LEXICAL_RECALL",
        "VECTOR_EMBEDDING",
        "GRAPH_EDGES",
        "MEMORY_BLOCK",
        "TEMPORAL",
        "PROVENANCE",
    }


def test_capabilities_support_set_algebra():
    source = {Capability.STORE, Capability.GRAPH_EDGES, Capability.PROVENANCE}
    target = {Capability.STORE, Capability.VECTOR_EMBEDDING, Capability.PROVENANCE}
    dropped = source - target
    assert dropped == {Capability.GRAPH_EDGES}
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/test_capabilities.py -v`
Expected: FAIL with `ImportError: cannot import name 'Capability'`

- [ ] **Step 3: Write minimal implementation**

```python
# src/coactra/memory/capabilities.py
"""Capability — the ONE vocabulary used by BOTH export negotiation and recall shaping.

A backend declares the subset it supports. export() intersects source and target sets;
the difference is what gets dropped/degraded (and reported). recall() callers pass the
subset THEY can consume so results are shaped to what they understand.
"""

from __future__ import annotations

from enum import Enum, auto


class Capability(Enum):
    STORE = auto()             # can persist/retrieve items at all (baseline)
    LEXICAL_RECALL = auto()    # token/substring matching
    VECTOR_EMBEDDING = auto()  # semantic similarity via embeddings
    GRAPH_EDGES = auto()       # typed relationships between items
    MEMORY_BLOCK = auto()      # Letta-style self-edited blocks
    TEMPORAL = auto()          # bitemporal validity (Graphiti-style)
    PROVENANCE = auto()        # preserves item lineage
```

```python
# src/coactra/memory/__init__.py  (extend imports + __all__)
from coactra.memory.capabilities import Capability
from coactra.memory.models import MemoryEvent, MemoryItem, Provenance
from coactra.memory.scope import Scope

__all__ = [
    "__version__",
    "Scope",
    "MemoryEvent",
    "MemoryItem",
    "Provenance",
    "Capability",
]
```

- [ ] **Step 4: Run test to verify it passes**

Run: `pytest tests/test_capabilities.py -v`
Expected: PASS (2 passed)

- [ ] **Step 5: Commit**

```bash
git add src/coactra/memory/capabilities.py src/coactra/memory/__init__.py tests/test_capabilities.py
git commit -m "feat(memory): Capability vocabulary shared by export + recall"
```

---

## Task 5: MemoryBackend Protocol (the SPI)

**Files:**
- Create: `src/coactra/memory/backend.py`
- Modify: `src/coactra/memory/__init__.py`
- Test: `tests/test_backend_protocol.py`

- [ ] **Step 1: Write the failing test**

```python
# tests/test_backend_protocol.py
from coactra.memory import Capability, MemoryBackend, MemoryEvent, MemoryItem, Scope


class _Dummy:
    def capabilities(self) -> set[Capability]:
        return {Capability.STORE}

    def learn(self, events, scope: Scope) -> list[MemoryItem]:
        return []

    def recall(self, query, scope, capabilities=None, limit=10):
        return []

    def dump(self, scope: Scope) -> list[MemoryItem]:
        return []

    def ingest(self, items, scope: Scope) -> list[MemoryItem]:
        return []


def test_protocol_is_runtime_checkable():
    assert isinstance(_Dummy(), MemoryBackend)


def test_incomplete_class_is_not_a_backend():
    class Partial:
        def learn(self, events, scope):
            return []

    assert not isinstance(Partial(), MemoryBackend)


def test_event_normalization_helper_accepts_str_and_event():
    from coactra.memory.backend import normalize_events

    out = normalize_events(["a plain string", MemoryEvent(content="already an event")])
    assert all(isinstance(e, MemoryEvent) for e in out)
    assert out[0].content == "a plain string"
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/test_backend_protocol.py -v`
Expected: FAIL with `ImportError: cannot import name 'MemoryBackend'`

- [ ] **Step 3: Write minimal implementation**

```python
# src/coactra/memory/backend.py
"""MemoryBackend — the swappable SPI.

Every method takes a Scope; isolation is part of the contract, not the caller's job.
dump()/ingest() are the export seam: dump() reads a scope's items out, ingest() writes
(possibly degraded) items into a target. The default InProcessBackend is the ONE working
implementation; mem0/graphiti/letta are optional-extra stubs.
"""

from __future__ import annotations

from collections.abc import Iterable, Sequence
from typing import Protocol, runtime_checkable

from coactra.memory.capabilities import Capability
from coactra.memory.models import MemoryEvent, MemoryItem
from coactra.memory.scope import Scope


def normalize_events(events: Iterable[str | MemoryEvent]) -> list[MemoryEvent]:
    """Accept plain strings or MemoryEvents; return MemoryEvents."""
    out: list[MemoryEvent] = []
    for e in events:
        out.append(e if isinstance(e, MemoryEvent) else MemoryEvent(content=e))
    return out


@runtime_checkable
class MemoryBackend(Protocol):
    def capabilities(self) -> set[Capability]:
        """Declare the Capability subset this backend supports."""
        ...

    def learn(self, events: Iterable[str | MemoryEvent], scope: Scope) -> list[MemoryItem]:
        """Consolidate conversational events into stored items within scope."""
        ...

    def recall(
        self,
        query: str,
        scope: Scope,
        capabilities: set[Capability] | None = None,
        limit: int = 10,
    ) -> list[MemoryItem]:
        """Retrieve items for query within scope, shaped to caller capabilities."""
        ...

    def dump(self, scope: Scope) -> list[MemoryItem]:
        """Read all items in scope (export source side)."""
        ...

    def ingest(self, items: Sequence[MemoryItem], scope: Scope) -> list[MemoryItem]:
        """Write items into scope (export target side)."""
        ...
```

```python
# src/coactra/memory/__init__.py  (extend imports + __all__)
from coactra.memory.backend import MemoryBackend
from coactra.memory.capabilities import Capability
from coactra.memory.models import MemoryEvent, MemoryItem, Provenance
from coactra.memory.scope import Scope

__all__ = [
    "__version__",
    "Scope",
    "MemoryEvent",
    "MemoryItem",
    "Provenance",
    "Capability",
    "MemoryBackend",
]
```

- [ ] **Step 4: Run test to verify it passes**

Run: `pytest tests/test_backend_protocol.py -v`
Expected: PASS (3 passed)

- [ ] **Step 5: Commit**

```bash
git add src/coactra/memory/backend.py src/coactra/memory/__init__.py tests/test_backend_protocol.py
git commit -m "feat(memory): MemoryBackend Protocol — the swappable, scope-first SPI"
```

---

## Task 6: InProcessBackend — learn + dedup (the default, part 1)

**Files:**
- Create: `src/coactra/memory/inprocess.py`
- Modify: `src/coactra/memory/__init__.py`
- Test: `tests/test_inprocess.py`

- [ ] **Step 1: Write the failing test**

```python
# tests/test_inprocess.py
from coactra.memory import Capability, InProcessBackend, MemoryEvent, Scope

SCOPE = Scope(tenant_id="acme", namespace="agent:1")


def test_learn_stores_items_with_provenance():
    be = InProcessBackend()
    items = be.learn(["dark mode preferred", MemoryEvent(content="deploy ok")], SCOPE)
    assert len(items) == 2
    assert all(i.provenance.source_backend == "inprocess" for i in items)
    assert {i.content for i in be.dump(SCOPE)} == {"dark mode preferred", "deploy ok"}


def test_learn_dedups_identical_content_in_scope():
    be = InProcessBackend()
    be.learn(["same lesson"], SCOPE)
    be.learn(["same lesson"], SCOPE)
    assert len(be.dump(SCOPE)) == 1


def test_capabilities_are_store_and_lexical():
    assert InProcessBackend().capabilities() == {
        Capability.STORE,
        Capability.LEXICAL_RECALL,
        Capability.PROVENANCE,
    }
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/test_inprocess.py -v`
Expected: FAIL with `ImportError: cannot import name 'InProcessBackend'`

- [ ] **Step 3: Write minimal implementation**

```python
# src/coactra/memory/inprocess.py
"""InProcessBackend — the ONE working default adapter.

Pydantic-only, no embeddings, no external service. Tenant-isolated dict keyed by
Scope.key. learn() stores typed items with trivial content-dedup (it does NOT run a
consolidation algorithm — smarter consolidation arrives by swapping in a real engine).
recall() is lexical token-overlap. This is the opinionated default that works out of
the box; advanced users swap the backend.
"""

from __future__ import annotations

from collections.abc import Iterable, Sequence

from coactra.memory.backend import normalize_events
from coactra.memory.capabilities import Capability
from coactra.memory.models import MemoryEvent, MemoryItem
from coactra.memory.scope import Scope

_SOURCE = "inprocess"


class InProcessBackend:
    """In-memory, tenant-isolated memory store."""

    def __init__(self) -> None:
        self._store: dict[str, list[MemoryItem]] = {}

    def capabilities(self) -> set[Capability]:
        return {Capability.STORE, Capability.LEXICAL_RECALL, Capability.PROVENANCE}

    def _bucket(self, scope: Scope) -> list[MemoryItem]:
        return self._store.setdefault(scope.key, [])

    def learn(self, events: Iterable[str | MemoryEvent], scope: Scope) -> list[MemoryItem]:
        bucket = self._bucket(scope)
        existing = {i.content for i in bucket}
        learned: list[MemoryItem] = []
        for event in normalize_events(events):
            if event.content in existing:
                continue
            item = MemoryItem.from_event(event, source_backend=_SOURCE)
            bucket.append(item)
            existing.add(event.content)
            learned.append(item)
        return learned

    def dump(self, scope: Scope) -> list[MemoryItem]:
        return list(self._bucket(scope))

    def ingest(self, items: Sequence[MemoryItem], scope: Scope) -> list[MemoryItem]:
        bucket = self._bucket(scope)
        existing = {i.content for i in bucket}
        added: list[MemoryItem] = []
        for item in items:
            if item.content in existing:
                continue
            bucket.append(item)
            existing.add(item.content)
            added.append(item)
        return added

    def recall(  # implemented in Task 7
        self,
        query: str,
        scope: Scope,
        capabilities: set[Capability] | None = None,
        limit: int = 10,
    ) -> list[MemoryItem]:
        raise NotImplementedError
```

```python
# src/coactra/memory/__init__.py  (extend imports + __all__)
from coactra.memory.backend import MemoryBackend
from coactra.memory.capabilities import Capability
from coactra.memory.inprocess import InProcessBackend
from coactra.memory.models import MemoryEvent, MemoryItem, Provenance
from coactra.memory.scope import Scope

__all__ = [
    "__version__",
    "Scope",
    "MemoryEvent",
    "MemoryItem",
    "Provenance",
    "Capability",
    "MemoryBackend",
    "InProcessBackend",
]
```

- [ ] **Step 4: Run test to verify it passes**

Run: `pytest tests/test_inprocess.py -v`
Expected: PASS (3 passed)

- [ ] **Step 5: Commit**

```bash
git add src/coactra/memory/inprocess.py src/coactra/memory/__init__.py tests/test_inprocess.py
git commit -m "feat(memory): InProcessBackend learn/dump/ingest with content dedup"
```

---

## Task 7: InProcessBackend — lexical, capability-shaped recall (default, part 2)

**Files:**
- Modify: `src/coactra/memory/inprocess.py`
- Test: `tests/test_inprocess_recall.py`

- [ ] **Step 1: Write the failing test**

```python
# tests/test_inprocess_recall.py
import pytest

from coactra.memory import Capability, InProcessBackend, Scope

SCOPE = Scope(tenant_id="acme", namespace="agent:1")


def _seeded():
    be = InProcessBackend()
    be.learn(
        [
            "deployment failed because the port was busy",
            "user prefers dark mode in the editor",
            "backup completed in 12 seconds",
        ],
        SCOPE,
    )
    return be


def test_recall_lexical_token_overlap_ranks_match_first():
    be = _seeded()
    out = be.recall("why did the deployment fail", SCOPE)
    assert out
    assert "deployment failed" in out[0].content


def test_recall_respects_limit():
    be = _seeded()
    out = be.recall("the", SCOPE, limit=1)
    assert len(out) <= 1


def test_recall_rejects_unsupported_requested_capability():
    be = _seeded()
    # Caller asks for VECTOR_EMBEDDING shaping the in-process backend can't provide.
    with pytest.raises(ValueError, match="VECTOR_EMBEDDING"):
        be.recall("deployment", SCOPE, capabilities={Capability.VECTOR_EMBEDDING})


def test_recall_accepts_supported_requested_capability():
    be = _seeded()
    out = be.recall("deployment", SCOPE, capabilities={Capability.LEXICAL_RECALL})
    assert out and "deployment failed" in out[0].content
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/test_inprocess_recall.py -v`
Expected: FAIL with `NotImplementedError`

- [ ] **Step 3: Write minimal implementation**

```python
# src/coactra/memory/inprocess.py  — replace the recall() stub with:

    @staticmethod
    def _tokens(text: str) -> set[str]:
        return {t for t in "".join(c if c.isalnum() else " " for c in text.lower()).split() if t}

    def recall(
        self,
        query: str,
        scope: Scope,
        capabilities: set[Capability] | None = None,
        limit: int = 10,
    ) -> list[MemoryItem]:
        if capabilities:
            unsupported = capabilities - self.capabilities()
            if unsupported:
                names = ", ".join(sorted(c.name for c in unsupported))
                raise ValueError(
                    f"InProcessBackend cannot shape recall to capabilities: {names}"
                )
        q = self._tokens(query)
        scored: list[tuple[int, MemoryItem]] = []
        for item in self._bucket(scope):
            overlap = len(q & self._tokens(item.content))
            if overlap:
                scored.append((overlap, item))
        scored.sort(key=lambda pair: pair[0], reverse=True)
        return [item for _, item in scored[:limit]]
```

- [ ] **Step 4: Run test to verify it passes**

Run: `pytest tests/test_inprocess_recall.py -v`
Expected: PASS (4 passed)

- [ ] **Step 5: Commit**

```bash
git add src/coactra/memory/inprocess.py tests/test_inprocess_recall.py
git commit -m "feat(memory): lexical, capability-validated recall on InProcessBackend"
```

---

## Task 8: Tenant isolation is real

**Files:**
- Test: `tests/test_isolation.py`

(No implementation — this proves the Scope key already isolates. If it fails, the bug is real.)

- [ ] **Step 1: Write the failing test**

```python
# tests/test_isolation.py
from coactra.memory import InProcessBackend, Scope

ACME = Scope(tenant_id="acme", namespace="shared")
GLOBEX = Scope(tenant_id="globex", namespace="shared")
ACME_OTHER_NS = Scope(tenant_id="acme", namespace="agent:2")


def test_tenant_cannot_read_other_tenants_items():
    be = InProcessBackend()
    be.learn(["acme secret"], ACME)
    be.learn(["globex secret"], GLOBEX)

    assert {i.content for i in be.dump(ACME)} == {"acme secret"}
    assert {i.content for i in be.dump(GLOBEX)} == {"globex secret"}
    assert be.recall("secret", GLOBEX)[0].content == "globex secret"


def test_namespaces_isolate_within_a_tenant():
    be = InProcessBackend()
    be.learn(["ns1 note"], ACME)
    assert be.dump(ACME_OTHER_NS) == []
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/test_isolation.py -v`
Expected: PASS immediately (isolation is structural via `Scope.key`). If it FAILS, fix `_bucket`/keying before proceeding.

- [ ] **Step 3: No implementation needed**

Isolation is enforced by `Scope.key` bucketing in `InProcessBackend`. This task locks it with a regression test.

- [ ] **Step 4: Run test to confirm green**

Run: `pytest tests/test_isolation.py -v`
Expected: PASS (2 passed)

- [ ] **Step 5: Commit**

```bash
git add tests/test_isolation.py
git commit -m "test(memory): lock tenant + namespace isolation as a regression guard"
```

---

## Task 9: ExportReport + lossy export (the core differentiator)

**Files:**
- Create: `src/coactra/memory/export.py`
- Modify: `src/coactra/memory/__init__.py`
- Test: `tests/test_export.py`

- [ ] **Step 1: Write the failing test**

```python
# tests/test_export.py
import pytest

from coactra.memory import (
    Capability,
    ExportReport,
    InProcessBackend,
    MemoryBackend,
    Scope,
    export,
)

SCOPE = Scope(tenant_id="acme", namespace="agent:1")


class _GraphBackend:
    """A fake source that claims graph + temporal capabilities the target lacks."""

    def __init__(self):
        self._inner = InProcessBackend()

    def capabilities(self):
        return {
            Capability.STORE,
            Capability.GRAPH_EDGES,
            Capability.TEMPORAL,
            Capability.PROVENANCE,
        }

    def learn(self, events, scope):
        return self._inner.learn(events, scope)

    def recall(self, query, scope, capabilities=None, limit=10):
        return self._inner.recall(query, scope, capabilities, limit)

    def dump(self, scope):
        return self._inner.dump(scope)

    def ingest(self, items, scope):
        return self._inner.ingest(items, scope)


def test_export_returns_report_and_moves_items():
    src = _GraphBackend()
    dst = InProcessBackend()
    src.learn(["a relationship between A and B", "an event at noon"], SCOPE)

    report = export(src, dst, scope=SCOPE)

    assert isinstance(report, ExportReport)
    assert report.transferred == 2
    assert {i.content for i in dst.dump(SCOPE)} == {
        "a relationship between A and B",
        "an event at noon",
    }


def test_export_reports_dropped_features_and_is_never_lossless():
    src = _GraphBackend()              # GRAPH_EDGES + TEMPORAL
    dst = InProcessBackend()           # neither
    src.learn(["x"], SCOPE)

    report = export(src, dst, scope=SCOPE)

    assert Capability.GRAPH_EDGES in report.dropped_capabilities
    assert Capability.TEMPORAL in report.dropped_capabilities
    assert report.lossless is False
    assert any("GRAPH_EDGES" in w for w in report.warnings)


def test_export_preserves_provenance_lineage():
    src = _GraphBackend()
    dst = InProcessBackend()
    src.learn(["traceable"], SCOPE)

    export(src, dst, scope=SCOPE)
    moved = dst.dump(SCOPE)[0]
    assert moved.provenance.exported_from is not None
    # export must COPY, not alias: the source's own item is untouched.
    assert src.dump(SCOPE)[0].provenance.exported_from is None


def test_same_capability_export_is_lossless():
    src = InProcessBackend()
    dst = InProcessBackend()
    src.learn(["plain note"], SCOPE)

    report = export(src, dst, scope=SCOPE)
    assert report.dropped_capabilities == set()
    assert report.lossless is True


def test_export_is_scope_isolated():
    src = InProcessBackend()
    dst = InProcessBackend()
    other = Scope(tenant_id="acme", namespace="agent:2")
    src.learn(["only in agent:1"], SCOPE)
    src.learn(["only in agent:2"], other)

    export(src, dst, scope=SCOPE)
    assert {i.content for i in dst.dump(SCOPE)} == {"only in agent:1"}
    assert dst.dump(other) == []


def test_backends_satisfy_protocol():
    assert isinstance(_GraphBackend(), MemoryBackend)
    assert isinstance(InProcessBackend(), MemoryBackend)
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/test_export.py -v`
Expected: FAIL with `ImportError: cannot import name 'ExportReport'`

- [ ] **Step 3: Write minimal implementation**

```python
# src/coactra/memory/export.py
"""Lossy export with capability negotiation, provenance, and an honest report.

export() NEVER promises lossless conversion. It intersects the source's and target's
declared Capability sets; everything the source has but the target lacks is recorded in
ExportReport.dropped_capabilities with a human-readable warning. Items still move (their
content + provenance survive), but features the target cannot represent are explicitly
reported as dropped/degraded — not silently lost.
"""

from __future__ import annotations

from pydantic import BaseModel, Field

from coactra.memory.backend import MemoryBackend
from coactra.memory.capabilities import Capability
from coactra.memory.scope import Scope


class ExportReport(BaseModel):
    """The honest record of a (lossy) export."""

    transferred: int = 0
    source_backend: str = ""
    target_backend: str = ""
    dropped_capabilities: set[Capability] = Field(default_factory=set)
    warnings: list[str] = Field(default_factory=list)

    @property
    def lossless(self) -> bool:
        """True only when no source capability was dropped at the target."""
        return not self.dropped_capabilities


def export(source: MemoryBackend, target: MemoryBackend, *, scope: Scope) -> ExportReport:
    src_caps = source.capabilities()
    dst_caps = target.capabilities()
    dropped = src_caps - dst_caps

    src_name = type(source).__name__
    dst_name = type(target).__name__

    # Deep-copy before mutating: dump() returns the source's own MemoryItem objects.
    # Mutating/ingesting them in place would alias source and target state and corrupt
    # the source's provenance. Copy, then stamp lineage on the copy.
    moved = []
    for item in source.dump(scope):
        copy = item.model_copy(deep=True)
        copy.provenance.exported_from = item.provenance.source_backend
        moved.append(copy)
    written = target.ingest(moved, scope)

    warnings = [
        f"target {dst_name} cannot represent {cap.name}; that feature was dropped"
        for cap in sorted(dropped, key=lambda c: c.name)
    ]
    return ExportReport(
        transferred=len(written),
        source_backend=src_name,
        target_backend=dst_name,
        dropped_capabilities=dropped,
        warnings=warnings,
    )
```

```python
# src/coactra/memory/__init__.py  (extend imports + __all__)
from coactra.memory.backend import MemoryBackend
from coactra.memory.capabilities import Capability
from coactra.memory.export import ExportReport, export
from coactra.memory.inprocess import InProcessBackend
from coactra.memory.models import MemoryEvent, MemoryItem, Provenance
from coactra.memory.scope import Scope

__all__ = [
    "__version__",
    "Scope",
    "MemoryEvent",
    "MemoryItem",
    "Provenance",
    "Capability",
    "MemoryBackend",
    "InProcessBackend",
    "ExportReport",
    "export",
]
```

- [ ] **Step 4: Run test to verify it passes**

Run: `pytest tests/test_export.py -v`
Expected: PASS (6 passed)

- [ ] **Step 5: Commit**

```bash
git add src/coactra/memory/export.py src/coactra/memory/__init__.py tests/test_export.py
git commit -m "feat(memory): lossy export — capability negotiation + provenance + ExportReport"
```

---

## Task 10: Optional-extra adapter stubs (SPI demonstration, raise on use)

**Files:**
- Create: `src/coactra/memory/adapters/__init__.py`
- Create: `src/coactra/memory/adapters/_stub.py`
- Create: `src/coactra/memory/adapters/mem0.py`
- Create: `src/coactra/memory/adapters/graphiti.py`
- Create: `src/coactra/memory/adapters/letta.py`
- Test: `tests/test_adapter_stubs.py`

- [ ] **Step 1: Write the failing test**

```python
# tests/test_adapter_stubs.py
import pytest

from coactra.memory import Capability
from coactra.memory.adapters._stub import MissingExtraError
from coactra.memory.adapters.graphiti import GraphitiBackend
from coactra.memory.adapters.letta import LettaBackend
from coactra.memory.adapters.mem0 import Mem0Backend


def test_stubs_declare_capabilities_without_the_extra():
    # Capability declaration is metadata — available even when the optional dep is absent.
    assert Capability.GRAPH_EDGES in GraphitiBackend.declared_capabilities
    assert Capability.MEMORY_BLOCK in LettaBackend.declared_capabilities
    assert Capability.VECTOR_EMBEDDING in Mem0Backend.declared_capabilities


@pytest.mark.parametrize("cls,extra", [
    (Mem0Backend, "mem0"),
    (GraphitiBackend, "graphiti"),
    (LettaBackend, "letta"),
])
def test_stub_instantiation_raises_until_extra_and_impl_land(cls, extra):
    with pytest.raises(MissingExtraError, match=extra):
        cls()
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/test_adapter_stubs.py -v`
Expected: FAIL with `ModuleNotFoundError: No module named 'coactra.memory.adapters'`

- [ ] **Step 3: Write minimal implementation**

```python
# src/coactra/memory/adapters/__init__.py
"""Optional-extra backend adapters. Stubs today — each demonstrates the MemoryBackend
SPI surface and raises MissingExtraError until its extra (and a real impl) land."""
```

```python
# src/coactra/memory/adapters/_stub.py
"""Shared helper for optional-extra adapter stubs."""

from __future__ import annotations


class MissingExtraError(RuntimeError):
    """Raised when an optional-extra backend is used before its extra/impl exist."""


def require_extra(extra: str) -> None:
    raise MissingExtraError(
        f"backend requires the optional '{extra}' extra and a real implementation; "
        f"install with: pip install coactra-memory[{extra}] (stub not yet implemented)"
    )
```

```python
# src/coactra/memory/adapters/mem0.py
"""Mem0 adapter — STUB. Declares capabilities; raises until the mem0 extra + impl land."""

from __future__ import annotations

from coactra.memory.adapters._stub import require_extra
from coactra.memory.capabilities import Capability


class Mem0Backend:
    declared_capabilities = {
        Capability.STORE,
        Capability.VECTOR_EMBEDDING,
        Capability.PROVENANCE,
    }

    def __init__(self, *args, **kwargs) -> None:
        require_extra("mem0")
```

```python
# src/coactra/memory/adapters/graphiti.py
"""Graphiti adapter — STUB. Declares graph/temporal capabilities; raises until graphiti extra."""

from __future__ import annotations

from coactra.memory.adapters._stub import require_extra
from coactra.memory.capabilities import Capability


class GraphitiBackend:
    declared_capabilities = {
        Capability.STORE,
        Capability.GRAPH_EDGES,
        Capability.TEMPORAL,
        Capability.PROVENANCE,
    }

    def __init__(self, *args, **kwargs) -> None:
        require_extra("graphiti")
```

```python
# src/coactra/memory/adapters/letta.py
"""Letta adapter — STUB. Declares memory-block capabilities; raises until letta extra."""

from __future__ import annotations

from coactra.memory.adapters._stub import require_extra
from coactra.memory.capabilities import Capability


class LettaBackend:
    declared_capabilities = {
        Capability.STORE,
        Capability.MEMORY_BLOCK,
        Capability.PROVENANCE,
    }

    def __init__(self, *args, **kwargs) -> None:
        require_extra("letta")
```

- [ ] **Step 4: Run test to verify it passes**

Run: `pytest tests/test_adapter_stubs.py -v`
Expected: PASS (4 passed)

- [ ] **Step 5: Commit**

```bash
git add src/coactra/memory/adapters tests/test_adapter_stubs.py
git commit -m "feat(memory): mem0/graphiti/letta adapter stubs (declare caps, raise on use)"
```

---

## Task 11: Full-suite green + public API lock

**Files:**
- Test: `tests/test_public_api.py`

- [ ] **Step 1: Write the failing test**

```python
# tests/test_public_api.py
import coactra.memory as m


def test_public_surface_is_complete():
    expected = {
        "__version__",
        "Scope",
        "MemoryEvent",
        "MemoryItem",
        "Provenance",
        "Capability",
        "MemoryBackend",
        "InProcessBackend",
        "ExportReport",
        "export",
    }
    assert expected <= set(m.__all__)
    for name in expected:
        assert hasattr(m, name), name


def test_end_to_end_learn_recall_export():
    src = m.InProcessBackend()
    dst = m.InProcessBackend()
    scope = m.Scope(tenant_id="acme", namespace="agent:1")

    src.learn(["the build broke on the linter step"], scope)
    hits = src.recall("why did the build break", scope)
    assert hits and "build broke" in hits[0].content

    report = m.export(src, dst, scope=scope)
    assert report.transferred == 1
    assert report.lossless is True
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/test_public_api.py -v`
Expected: FAIL (file/test not yet present) — then becomes PASS once added since the API already exists from prior tasks.

- [ ] **Step 3: No new implementation**

The public API was assembled incrementally in Tasks 1–10. This task only adds the end-to-end + surface-lock test.

- [ ] **Step 4: Run the full suite**

Run: `pytest -v`
Expected: PASS (all tests across all files green)

- [ ] **Step 5: Commit**

```bash
git add tests/test_public_api.py
git commit -m "test(memory): lock public API surface + end-to-end learn/recall/export"
```

---

## Self-Review Checklist (run after implementing)

1. **Charter coverage** — `learn`/`recall`/`export` present (Tasks 6/7/9); export is lossy with capability negotiation + provenance + unsupported-feature report (Task 9); never claims lossless on a real drop (`test_export_reports_dropped_features_and_is_never_lossless`). ✔
2. **Principles** — THIN (default is a dict store, no engine reimplemented); Protocol + ONE working default + stubs (Tasks 5/6/7/10); Scope on every call and isolation proven (Task 8); opinionated default works out of the box (Task 11). ✔
3. **Packaging** — PEP 420 namespace (no `src/coactra/__init__.py`, Task 1 test asserts it), src layout, `py.typed`, hatchling, optional extras. ✔
4. **Boundary** — memory learns from conversation; no shared store with lib-ai reasoning-capture (stated in module docstrings). ✔
5. **Type consistency** — `Scope.key`, `MemoryItem.from_event(source_backend=...)`, `Provenance.exported_from`, `Capability` names, `MemoryBackend` (capabilities/learn/recall/dump/ingest), `ExportReport.lossless` used identically across tasks. ✔
