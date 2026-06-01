# coactra.ai Implementation Plan

> **Current layout note:** the original flat module paths below remain compatibility imports.
> Canonical implementation now lives under `completion/` (provider calls and embeddings)
> and `replay/` (capture, gate, models, and store).

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Ship a thin, publishable foundation library that (a) wraps LiteLLM + Instructor as a small model-call / structured-output shelf, and (b) builds the one novel core — reasoning capture-replay with an adaptive gate, bounded quality-filtered retrieval, and an explicit replay-vs-re-reason fallback.

**Architecture:** Two surfaces in one distribution. The **wrap shelf** (`client.ask` over LiteLLM, `structured()` over Instructor) is trivial passthrough — never re-implement provider routing or typing. The **novel core** is orchestration: `capture()` stores a `ReasoningTrace` (problem text + embedding + reasoning + outcome stats) into a tenant-scoped `ReasoningStore`; `recall_or_reason()` runs the pipeline `embed → bounded+quality-filtered retrieve → adaptive gate → replay | re-reason`. The gate is adaptive because `record_outcome(trace_id, success)` feeds observed correctness back into each trace, and the accept boundary is computed from neighbors' verified success — the *same* signal that powers the quality filter (one unified guard). Backends are swapped via `typing.Protocol`s with exactly one working default each.

**Tech Stack:** Python 3.12+, hatchling (PEP 420 namespace package `coactra/ai/`), pydantic v2, litellm, instructor, numpy (cosine similarity + default embedding via `litellm.embedding`), pytest. chromadb is an optional, stubbed adapter.

---

## File Structure

| File | Single responsibility |
|------|----------------------|
| `pyproject.toml` | Hatchling build of the PEP 420 namespace package; runtime deps (instructor, litellm, pydantic, numpy); optional-deps groups (`chroma`, `dev`). |
| `src/coactra/ai/__init__.py` | Public surface (matches Task 9 `__all__`): `ask`, `structured`, `LiteLLMCompleter`, `LiteLLMEmbedding`, `cosine`, `ReasoningEngine`, `AdaptiveGate`, `InMemoryStore`, `ReasoningTrace`, `RecallResult`, `Decision`. `capture`/`recall_or_reason`/`record_outcome` are `ReasoningEngine` methods, not module functions. No `src/coactra/__init__.py` (namespace). |
| `src/coactra/ai/py.typed` | PEP 561 typing marker. |
| `src/coactra/ai/protocols.py` | `EmbeddingFn`, `Completer`, `ReasoningStore` Protocols — the swap seams (one default adapter each). |
| `src/coactra/ai/models.py` | `ReasoningTrace` (pydantic) with outcome stats + `quality` property; `Decision` enum; `RecallResult` dataclass. |
| `src/coactra/ai/client.py` | Wrap shelf: `ask()` (LiteLLM completion) and `structured()` (Instructor typed output). Default `Completer`. |
| `src/coactra/ai/embedding.py` | Default `EmbeddingFn` over `litellm.embedding`; `cosine()` numpy helper. |
| `src/coactra/ai/store.py` | `InMemoryStore` — the one default `ReasoningStore`, tenant-partitioned, bounded quality-filtered retrieval. |
| `src/coactra/ai/gate.py` | `AdaptiveGate` — accept boundary computed from neighbors' verified outcomes (vCache-style), not a static threshold. |
| `src/coactra/ai/engine.py` | `ReasoningEngine` — `capture / recall_or_reason / record_outcome` orchestration; the three replay-vs-re-reason branches. |
| `src/coactra/ai/adapters/__init__.py` | Adapter namespace. |
| `src/coactra/ai/adapters/chroma.py` | Optional `ChromaStore` stub adapter (raises if `chromadb` missing). |
| `tests/test_packaging.py` | Namespace import + no `src/coactra/__init__.py`. |
| `tests/test_client.py` | Wrap shelf with injected fake `Completer`. |
| `tests/test_embedding.py` | Cosine + default embedding shape (mocked). |
| `tests/test_store.py` | Tenant isolation, bounded cap, quality filtering. |
| `tests/test_gate.py` | Accept boundary MOVES with outcomes (the discriminating test). |
| `tests/test_engine.py` | Capture → replay; three fallback branches; outcome feedback. |

---

### Task 1: Packaging — PEP 420 namespace package imports

**Files:**
- Create: `pyproject.toml`
- Create: `src/coactra/ai/__init__.py`
- Create: `src/coactra/ai/py.typed`
- Test: `tests/test_packaging.py`

- [ ] **Step 1: Write the failing test**

```python
# tests/test_packaging.py
import importlib
import pathlib


def test_namespace_package_imports():
    mod = importlib.import_module("coactra.ai")
    assert mod.__name__ == "coactra.ai"


def test_no_top_level_init():
    # PEP 420: coactra must NOT have its own __init__.py
    root = pathlib.Path(__file__).resolve().parent.parent
    assert not (root / "src" / "coactra" / "__init__.py").exists()
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
name = "coactra-ai"
version = "0.1.0"
description = "Model-call shelf + reasoning capture-replay for AI agent fleets."
readme = "README.md"
requires-python = ">=3.12"
license = { text = "MIT" }
dependencies = [
    "instructor>=1.0",
    "litellm>=1.40",
    "pydantic>=2.6",
    "numpy>=1.26",
]

[project.optional-dependencies]
chroma = ["chromadb>=0.5"]
dev = ["pytest>=8.0"]

[tool.hatch.build.targets.wheel]
packages = ["src/coactra"]

[tool.pytest.ini_options]
pythonpath = ["src"]
testpaths = ["tests"]
```

```python
# src/coactra/ai/__init__.py
"""coactra.ai — model-call shelf + reasoning capture-replay."""

__all__ = []
```

```text
# src/coactra/ai/py.typed
```

- [ ] **Step 4: Run test to verify it passes**

Run: `pytest tests/test_packaging.py -v`
Expected: PASS (2 passed)

- [ ] **Step 5: Commit**

```bash
git add pyproject.toml src/coactra/ai/__init__.py src/coactra/ai/py.typed tests/test_packaging.py
git commit -m "feat(ai): PEP 420 namespace package skeleton"
```

---

### Task 2: Protocols — the swap seams

**Files:**
- Create: `src/coactra/ai/protocols.py`
- Test: `tests/test_protocols.py`

- [ ] **Step 1: Write the failing test**

```python
# tests/test_protocols.py
from coactra.ai.protocols import EmbeddingFn, ReasoningStore, Completer


def test_protocols_are_runtime_checkable():
    class FakeEmbed:
        def __call__(self, text: str) -> list[float]:
            return [0.0]

    assert isinstance(FakeEmbed(), EmbeddingFn)


def test_completer_protocol_shape():
    class FakeCompleter:
        def complete(self, model: str, messages: list[dict], **kw) -> str:
            return "ok"

    assert isinstance(FakeCompleter(), Completer)


def test_reasoning_store_protocol_shape():
    class FakeStore:
        def put(self, tenant, trace): ...
        def search(self, tenant, vector, k, min_quality): return []
        def get(self, tenant, trace_id): return None

    assert isinstance(FakeStore(), ReasoningStore)
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/test_protocols.py -v`
Expected: FAIL with `ModuleNotFoundError: No module named 'coactra.ai.protocols'`

- [ ] **Step 3: Write minimal implementation**

```python
# src/coactra/ai/protocols.py
"""Swap seams: one Protocol per backend, exactly one default adapter each."""
from __future__ import annotations

from typing import Any, Protocol, runtime_checkable


@runtime_checkable
class EmbeddingFn(Protocol):
    def __call__(self, text: str) -> list[float]: ...


@runtime_checkable
class Completer(Protocol):
    def complete(self, model: str, messages: list[dict[str, Any]], **kwargs: Any) -> str: ...


@runtime_checkable
class ReasoningStore(Protocol):
    """Procedural-memory record store (cosine nearest-neighbour over embeddings), tenant-partitioned."""

    def put(self, tenant: str, trace: Any) -> None: ...

    def search(
        self, tenant: str, vector: list[float], k: int, min_quality: float
    ) -> list[tuple[Any, float]]:
        """Bounded + quality-filtered: <=k traces with quality>=min_quality, (trace, similarity)."""
        ...

    def get(self, tenant: str, trace_id: str) -> Any | None: ...
```

- [ ] **Step 4: Run test to verify it passes**

Run: `pytest tests/test_protocols.py -v`
Expected: PASS (3 passed)

- [ ] **Step 5: Commit**

```bash
git add src/coactra/ai/protocols.py tests/test_protocols.py
git commit -m "feat(ai): backend swap Protocols (embedding, completer, reasoning store)"
```

---

### Task 3: Models — ReasoningTrace with outcome feedback

**Files:**
- Create: `src/coactra/ai/models.py`
- Test: `tests/test_models.py`

The outcome-feedback seam is load-bearing: `quality` is computed from observed correctness, and the *same* signal powers both the adaptive gate and the quality filter.

- [ ] **Step 1: Write the failing test**

```python
# tests/test_models.py
from coactra.ai.models import ReasoningTrace, Decision


def test_trace_starts_neutral_quality():
    t = ReasoningTrace(id="t1", problem="p", reasoning="r", embedding=[0.1])
    # no outcomes yet -> neutral prior (0.5), not 0 and not 1
    assert t.quality == 0.5
    assert t.successes == 0 and t.failures == 0


def test_quality_tracks_outcomes():
    t = ReasoningTrace(id="t1", problem="p", reasoning="r", embedding=[0.1])
    t.record(True)
    t.record(True)
    t.record(False)
    # Laplace-smoothed success rate: (2+1)/(3+2) = 0.6
    assert abs(t.quality - 0.6) < 1e-9
    assert t.successes == 2 and t.failures == 1


def test_decision_enum_values():
    assert {d.value for d in Decision} == {"replay", "re_reason"}
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/test_models.py -v`
Expected: FAIL with `ModuleNotFoundError: No module named 'coactra.ai.models'`

- [ ] **Step 3: Write minimal implementation**

```python
# src/coactra/ai/models.py
"""Procedural-memory record + decision types."""
from __future__ import annotations

import enum
from dataclasses import dataclass

from pydantic import BaseModel, Field


class Decision(str, enum.Enum):
    REPLAY = "replay"
    RE_REASON = "re_reason"


class ReasoningTrace(BaseModel):
    """One captured reasoning path. Quality is learned from replay outcomes."""

    id: str
    problem: str
    reasoning: str
    embedding: list[float]
    successes: int = 0
    failures: int = 0
    meta: dict = Field(default_factory=dict)

    @property
    def quality(self) -> float:
        """Laplace-smoothed success rate; neutral 0.5 prior with no data."""
        return (self.successes + 1) / (self.successes + self.failures + 2)

    def record(self, success: bool) -> None:
        if success:
            self.successes += 1
        else:
            self.failures += 1


@dataclass
class RecallResult:
    decision: Decision
    answer: str
    trace_id: str | None
    confidence: float
    reasoned_fresh: bool
```

- [ ] **Step 4: Run test to verify it passes**

Run: `pytest tests/test_models.py -v`
Expected: PASS (3 passed)

- [ ] **Step 5: Commit**

```bash
git add src/coactra/ai/models.py tests/test_models.py
git commit -m "feat(ai): ReasoningTrace record with learned quality from outcomes"
```

---

### Task 4: Embedding — default EmbeddingFn + cosine

**Files:**
- Create: `src/coactra/ai/embedding.py`
- Test: `tests/test_embedding.py`

- [ ] **Step 1: Write the failing test**

```python
# tests/test_embedding.py
from unittest.mock import patch

from coactra.ai.embedding import cosine, LiteLLMEmbedding


def test_cosine_identical_is_one():
    assert abs(cosine([1.0, 0.0], [1.0, 0.0]) - 1.0) < 1e-9


def test_cosine_orthogonal_is_zero():
    assert abs(cosine([1.0, 0.0], [0.0, 1.0])) < 1e-9


def test_cosine_zero_vector_is_safe():
    assert cosine([0.0, 0.0], [1.0, 0.0]) == 0.0


def test_default_embedding_uses_litellm():
    fake = {"data": [{"embedding": [0.1, 0.2, 0.3]}]}
    with patch("coactra.ai.embedding.litellm.embedding", return_value=fake) as m:
        embed = LiteLLMEmbedding(model="text-embedding-3-small")
        out = embed("hello")
    assert out == [0.1, 0.2, 0.3]
    m.assert_called_once()
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/test_embedding.py -v`
Expected: FAIL with `ModuleNotFoundError: No module named 'coactra.ai.embedding'`

- [ ] **Step 3: Write minimal implementation**

```python
# src/coactra/ai/embedding.py
"""Default EmbeddingFn over litellm.embedding + numpy cosine."""
from __future__ import annotations

import litellm
import numpy as np


def cosine(a: list[float], b: list[float]) -> float:
    va, vb = np.asarray(a, dtype=float), np.asarray(b, dtype=float)
    na, nb = np.linalg.norm(va), np.linalg.norm(vb)
    if na == 0.0 or nb == 0.0:
        return 0.0
    return float(np.dot(va, vb) / (na * nb))


class LiteLLMEmbedding:
    """Opinionated default EmbeddingFn. Swap by passing any callable to the engine."""

    def __init__(self, model: str = "text-embedding-3-small") -> None:
        self.model = model

    def __call__(self, text: str) -> list[float]:
        resp = litellm.embedding(model=self.model, input=[text])
        return list(resp["data"][0]["embedding"])
```

- [ ] **Step 4: Run test to verify it passes**

Run: `pytest tests/test_embedding.py -v`
Expected: PASS (4 passed)

- [ ] **Step 5: Commit**

```bash
git add src/coactra/ai/embedding.py tests/test_embedding.py
git commit -m "feat(ai): default litellm embedding + numpy cosine"
```

---

### Task 5: InMemoryStore — tenant isolation, bounded + quality-filtered retrieval

**Files:**
- Create: `src/coactra/ai/store.py`
- Test: `tests/test_store.py`

- [ ] **Step 1: Write the failing test**

```python
# tests/test_store.py
from coactra.ai.models import ReasoningTrace
from coactra.ai.store import InMemoryStore


def _trace(id, vec, succ=0, fail=0):
    t = ReasoningTrace(id=id, problem=id, reasoning="r", embedding=vec)
    t.successes, t.failures = succ, fail
    return t


def test_tenant_isolation():
    s = InMemoryStore()
    s.put("tenant-a", _trace("t1", [1.0, 0.0]))
    # tenant-b sees nothing
    assert s.search("tenant-b", [1.0, 0.0], k=5, min_quality=0.0) == []
    assert s.get("tenant-b", "t1") is None
    assert s.get("tenant-a", "t1") is not None


def test_search_is_bounded_by_k():
    s = InMemoryStore()
    for i in range(10):
        s.put("a", _trace(f"t{i}", [1.0, 0.0], succ=5))
    hits = s.search("a", [1.0, 0.0], k=3, min_quality=0.0)
    assert len(hits) == 3


def test_search_filters_low_quality():
    s = InMemoryStore()
    s.put("a", _trace("good", [1.0, 0.0], succ=9, fail=0))   # quality ~0.91
    s.put("a", _trace("bad", [1.0, 0.0], succ=0, fail=9))    # quality ~0.09
    hits = s.search("a", [1.0, 0.0], k=5, min_quality=0.5)
    ids = [t.id for t, _ in hits]
    assert ids == ["good"]


def test_search_orders_by_similarity():
    s = InMemoryStore()
    s.put("a", _trace("near", [1.0, 0.0], succ=5))
    s.put("a", _trace("far", [0.0, 1.0], succ=5))
    hits = s.search("a", [1.0, 0.1], k=5, min_quality=0.0)
    assert hits[0][0].id == "near"
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/test_store.py -v`
Expected: FAIL with `ModuleNotFoundError: No module named 'coactra.ai.store'`

- [ ] **Step 3: Write minimal implementation**

```python
# src/coactra/ai/store.py
"""Default ReasoningStore: in-process, tenant-partitioned, bounded + quality-filtered."""
from __future__ import annotations

from coactra.ai.embedding import cosine
from coactra.ai.models import ReasoningTrace


class InMemoryStore:
    """The one working default. Swap via the ReasoningStore Protocol."""

    def __init__(self) -> None:
        self._by_tenant: dict[str, dict[str, ReasoningTrace]] = {}

    def put(self, tenant: str, trace: ReasoningTrace) -> None:
        self._by_tenant.setdefault(tenant, {})[trace.id] = trace

    def get(self, tenant: str, trace_id: str) -> ReasoningTrace | None:
        return self._by_tenant.get(tenant, {}).get(trace_id)

    def search(
        self, tenant: str, vector: list[float], k: int, min_quality: float
    ) -> list[tuple[ReasoningTrace, float]]:
        traces = self._by_tenant.get(tenant, {}).values()
        scored = [
            (t, cosine(vector, t.embedding))
            for t in traces
            if t.quality >= min_quality
        ]
        scored.sort(key=lambda pair: pair[1], reverse=True)
        return scored[:k]
```

- [ ] **Step 4: Run test to verify it passes**

Run: `pytest tests/test_store.py -v`
Expected: PASS (4 passed)

- [ ] **Step 5: Commit**

```bash
git add src/coactra/ai/store.py tests/test_store.py
git commit -m "feat(ai): InMemoryStore with tenant isolation + bounded quality-filtered search"
```

---

### Task 6: AdaptiveGate — accept boundary MOVES with outcomes

**Files:**
- Create: `src/coactra/ai/gate.py`
- Test: `tests/test_gate.py`

This is the highest-risk task. The discriminating test asserts the accept boundary **moves** as verified outcomes accumulate — a static threshold would fail it. The gate is vCache-style: a candidate is accepted only when neighbour similarity clears a bar that is *lowered by verified success and raised by failure*.

- [ ] **Step 1: Write the failing test**

```python
# tests/test_gate.py
from coactra.ai.gate import AdaptiveGate
from coactra.ai.models import ReasoningTrace


def _trace(succ, fail):
    return ReasoningTrace(id="t", problem="p", reasoning="r", embedding=[1.0], successes=succ, failures=fail)


def test_boundary_moves_with_outcomes():
    gate = AdaptiveGate(base_threshold=0.90)
    sim = 0.85  # below the static base bar

    # Untrusted trace (no verified successes): borderline sim is REJECTED.
    cold = _trace(succ=0, fail=0)
    assert gate.accept(similarity=sim, trace=cold) is False

    # Same similarity, same trace once it has many verified-correct replays:
    # the required bar drops below 0.85 -> now ACCEPTED. Boundary moved.
    proven = _trace(succ=20, fail=0)
    assert gate.accept(similarity=sim, trace=proven) is True


def test_failures_raise_the_bar():
    gate = AdaptiveGate(base_threshold=0.90)
    # A trace that has failed a lot must clear a HIGHER bar than a fresh one.
    bad = _trace(succ=0, fail=20)
    good = _trace(succ=20, fail=0)
    assert gate.required(bad) > gate.required(good)


def test_required_never_below_floor():
    gate = AdaptiveGate(base_threshold=0.90, floor=0.70)
    perfect = _trace(succ=1000, fail=0)
    assert gate.required(perfect) >= 0.70


def test_confidence_combines_similarity_and_quality():
    gate = AdaptiveGate(base_threshold=0.90)
    proven = _trace(succ=20, fail=0)
    c = gate.confidence(similarity=0.85, trace=proven)
    assert 0.0 <= c <= 1.0
    # higher quality -> higher confidence at equal similarity
    weak = _trace(succ=0, fail=0)
    assert gate.confidence(0.85, proven) > gate.confidence(0.85, weak)
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/test_gate.py -v`
Expected: FAIL with `ModuleNotFoundError: No module named 'coactra.ai.gate'`

- [ ] **Step 3: Write minimal implementation**

```python
# src/coactra/ai/gate.py
"""Adaptive (vCache-style) accept gate.

Not a static threshold: the similarity a candidate must clear is adjusted by the
candidate's *verified* track record. Proven traces (high quality) earn a lower bar;
traces that have failed must clear a higher bar. The boundary moves as outcomes
accumulate via ReasoningTrace.record(...)/quality.
"""
from __future__ import annotations

from coactra.ai.models import ReasoningTrace


class AdaptiveGate:
    def __init__(
        self, base_threshold: float = 0.90, floor: float = 0.70, span: float = 0.20
    ) -> None:
        self.base_threshold = base_threshold
        self.floor = floor
        self.span = span

    def required(self, trace: ReasoningTrace) -> float:
        """Similarity bar for this trace. quality 0.5 -> base; ->1 lowers, ->0 raises."""
        # quality in [0,1]; shift = (quality - 0.5) * 2 * span, clamped to floor.
        adjusted = self.base_threshold - (trace.quality - 0.5) * 2.0 * self.span
        return max(self.floor, adjusted)

    def accept(self, similarity: float, trace: ReasoningTrace) -> bool:
        return similarity >= self.required(trace)

    def confidence(self, similarity: float, trace: ReasoningTrace) -> float:
        c = similarity * trace.quality
        return max(0.0, min(1.0, c))
```

- [ ] **Step 4: Run test to verify it passes**

Run: `pytest tests/test_gate.py -v`
Expected: PASS (4 passed)

- [ ] **Step 5: Commit**

```bash
git add src/coactra/ai/gate.py tests/test_gate.py
git commit -m "feat(ai): adaptive vCache-style gate whose boundary moves with verified outcomes"
```

---

### Task 7: Client — the wrap shelf (LiteLLM + Instructor)

**Files:**
- Create: `src/coactra/ai/client.py`
- Test: `tests/test_client.py`

Stays trivial — passthrough only. No retries/streaming/gold-plating.

- [ ] **Step 1: Write the failing test**

```python
# tests/test_client.py
from unittest.mock import MagicMock, patch

from pydantic import BaseModel

from coactra.ai.client import ask, structured, LiteLLMCompleter


def test_ask_passes_through_to_completer():
    fake = MagicMock()
    fake.complete.return_value = "hi there"
    out = ask("say hi", model="gpt-4o-mini", completer=fake)
    assert out == "hi there"
    fake.complete.assert_called_once()


def test_litellm_completer_extracts_content():
    resp = {"choices": [{"message": {"content": "yo"}}]}
    with patch("coactra.ai.client.litellm.completion", return_value=resp):
        out = LiteLLMCompleter().complete("gpt-4o-mini", [{"role": "user", "content": "x"}])
    assert out == "yo"


def test_structured_uses_instructor_response_model():
    class Person(BaseModel):
        name: str

    fake_client = MagicMock()
    fake_client.chat.completions.create.return_value = Person(name="Ada")
    with patch("coactra.ai.client.instructor.from_litellm", return_value=fake_client):
        out = structured(Person, "who?", model="gpt-4o-mini")
    assert out == Person(name="Ada")
    _, kwargs = fake_client.chat.completions.create.call_args
    assert kwargs["response_model"] is Person
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/test_client.py -v`
Expected: FAIL with `ModuleNotFoundError: No module named 'coactra.ai.client'`

- [ ] **Step 3: Write minimal implementation**

```python
# src/coactra/ai/client.py
"""Wrap shelf. LiteLLM routes; Instructor types. We add nothing but the seam."""
from __future__ import annotations

from typing import Any, TypeVar

import instructor
import litellm
from pydantic import BaseModel

from coactra.ai.protocols import Completer

T = TypeVar("T", bound=BaseModel)


class LiteLLMCompleter:
    """Default Completer over litellm.completion."""

    def complete(self, model: str, messages: list[dict[str, Any]], **kwargs: Any) -> str:
        resp = litellm.completion(model=model, messages=messages, **kwargs)
        return resp["choices"][0]["message"]["content"]


def ask(
    prompt: str,
    *,
    model: str = "gpt-4o-mini",
    completer: Completer | None = None,
    **kwargs: Any,
) -> str:
    """Call any model for free-text. completer is swappable; default = LiteLLM."""
    completer = completer or LiteLLMCompleter()
    return completer.complete(model, [{"role": "user", "content": prompt}], **kwargs)


def structured(
    schema: type[T],
    prompt: str,
    *,
    model: str = "gpt-4o-mini",
    **kwargs: Any,
) -> T:
    """Typed output via Instructor (response_model enforcement) over LiteLLM."""
    client = instructor.from_litellm(litellm.completion)
    return client.chat.completions.create(
        model=model,
        messages=[{"role": "user", "content": prompt}],
        response_model=schema,
        **kwargs,
    )
```

- [ ] **Step 4: Run test to verify it passes**

Run: `pytest tests/test_client.py -v`
Expected: PASS (3 passed)

- [ ] **Step 5: Commit**

```bash
git add src/coactra/ai/client.py tests/test_client.py
git commit -m "feat(ai): wrap shelf — ask() over LiteLLM, structured() over Instructor"
```

---

### Task 8: ReasoningEngine — capture → gate → bounded-retrieve → replay-or-fallback

**Files:**
- Create: `src/coactra/ai/engine.py`
- Test: `tests/test_engine.py`

The novel core. Three explicit branches: (A) high-confidence accepted candidate → **replay**; (B) candidate found but gate rejects → **re-reason**; (C) no quality candidate at all → **re-reason**. `record_outcome` feeds the trace, closing the adaptive loop. All tests inject fakes — zero network.

- [ ] **Step 1: Write the failing test**

```python
# tests/test_engine.py
from coactra.ai.engine import ReasoningEngine
from coactra.ai.models import Decision
from coactra.ai.store import InMemoryStore


class FixedEmbed:
    """Maps known problems to fixed vectors so similarity is deterministic."""

    def __init__(self, table):
        self.table = table

    def __call__(self, text):
        return self.table.get(text, [0.0, 0.0])


def make_engine(table, reasoner):
    return ReasoningEngine(
        store=InMemoryStore(),
        embed=FixedEmbed(table),
        reasoner=reasoner,
        k=3,
        min_quality=0.4,
    )


def test_capture_then_replay_on_similar_problem():
    table = {"P1": [1.0, 0.0], "P1b": [1.0, 0.01]}
    calls = []
    eng = make_engine(table, lambda p: calls.append(p) or "FRESH")

    tid = eng.capture("tenant", "P1", "REASON-1")
    # mark it proven so the adaptive gate lowers the bar
    for _ in range(20):
        eng.record_outcome("tenant", tid, True)

    res = eng.recall_or_reason("tenant", "P1b")
    assert res.decision == Decision.REPLAY
    assert res.answer == "REASON-1"
    assert res.reasoned_fresh is False
    assert calls == []  # reasoner NOT called


def test_branch_b_candidate_but_gate_rejects_re_reasons():
    table = {"P1": [1.0, 0.0], "FAR": [0.2, 1.0]}
    eng = make_engine(table, lambda p: "FRESH")
    tid = eng.capture("tenant", "P1", "REASON-1")
    for _ in range(20):
        eng.record_outcome("tenant", tid, True)

    # FAR is too dissimilar -> even a proven trace can't clear the bar.
    res = eng.recall_or_reason("tenant", "FAR")
    assert res.decision == Decision.RE_REASON
    assert res.answer == "FRESH"
    assert res.reasoned_fresh is True


def test_branch_c_no_quality_candidate_re_reasons():
    table = {"P1": [1.0, 0.0], "P1b": [1.0, 0.01]}
    eng = make_engine(table, lambda p: "FRESH")
    tid = eng.capture("tenant", "P1", "REASON-1")
    # poison quality below min_quality -> filtered out before the gate
    for _ in range(20):
        eng.record_outcome("tenant", tid, False)

    res = eng.recall_or_reason("tenant", "P1b")
    assert res.decision == Decision.RE_REASON
    assert res.answer == "FRESH"


def test_re_reason_auto_captures_for_next_time():
    table = {"P1": [1.0, 0.0]}
    eng = make_engine(table, lambda p: "FRESH-REASONING")
    res = eng.recall_or_reason("tenant", "P1")  # cold: nothing stored
    assert res.decision == Decision.RE_REASON
    # the fresh reasoning is now captured and replayable
    assert eng.store.get("tenant", res.trace_id) is not None


def test_tenant_isolation_in_recall():
    table = {"P1": [1.0, 0.0]}
    eng = make_engine(table, lambda p: "FRESH")
    tid = eng.capture("tenant-a", "P1", "REASON-A")
    for _ in range(20):
        eng.record_outcome("tenant-a", tid, True)
    # tenant-b asks the same problem -> miss -> re-reason
    res = eng.recall_or_reason("tenant-b", "P1")
    assert res.decision == Decision.RE_REASON
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/test_engine.py -v`
Expected: FAIL with `ModuleNotFoundError: No module named 'coactra.ai.engine'`

- [ ] **Step 3: Write minimal implementation**

```python
# src/coactra/ai/engine.py
"""The novel core: capture -> gate -> bounded retrieve -> replay-or-fallback.

Guardrails (all enforced here):
  1. ADAPTIVE gate (AdaptiveGate) — not a static threshold.
  2. BOUNDED + quality-filtered retrieval (store.search with k + min_quality).
  3. Explicit REPLAY vs RE-REASON fallback — three branches below.
Multi-tenant: `tenant` threads through every call; the store partitions on it.
"""
from __future__ import annotations

import uuid
from typing import Callable

from coactra.ai.gate import AdaptiveGate
from coactra.ai.models import Decision, ReasoningTrace, RecallResult
from coactra.ai.protocols import EmbeddingFn, ReasoningStore

Reasoner = Callable[[str], str]


class ReasoningEngine:
    def __init__(
        self,
        store: ReasoningStore,
        embed: EmbeddingFn,
        reasoner: Reasoner,
        *,
        gate: AdaptiveGate | None = None,
        k: int = 3,
        min_quality: float = 0.4,
    ) -> None:
        self.store = store
        self.embed = embed
        self.reasoner = reasoner
        self.gate = gate or AdaptiveGate()
        self.k = k
        self.min_quality = min_quality

    def capture(self, tenant: str, problem: str, reasoning: str, **meta) -> str:
        trace = ReasoningTrace(
            id=uuid.uuid4().hex,
            problem=problem,
            reasoning=reasoning,
            embedding=self.embed(problem),
            meta=meta,
        )
        self.store.put(tenant, trace)
        return trace.id

    def record_outcome(self, tenant: str, trace_id: str, success: bool) -> None:
        trace = self.store.get(tenant, trace_id)
        if trace is None:
            return
        trace.record(success)
        self.store.put(tenant, trace)  # persist updated stats

    def recall_or_reason(self, tenant: str, problem: str) -> RecallResult:
        vector = self.embed(problem)
        # Guard 2: bounded + quality-filtered retrieval.
        hits = self.store.search(tenant, vector, k=self.k, min_quality=self.min_quality)

        # Branch C: no quality candidate -> re-reason.
        if hits:
            trace, similarity = hits[0]
            # Branch A: adaptive gate accepts -> replay.
            if self.gate.accept(similarity, trace):
                # Outcome of this replay is reported later via record_outcome().
                return RecallResult(
                    decision=Decision.REPLAY,
                    answer=trace.reasoning,
                    trace_id=trace.id,
                    confidence=self.gate.confidence(similarity, trace),
                    reasoned_fresh=False,
                )
            # Branch B: candidate exists but gate rejects -> re-reason (fall through).

        fresh = self.reasoner(problem)
        new_id = self.capture(tenant, problem, fresh)
        return RecallResult(
            decision=Decision.RE_REASON,
            answer=fresh,
            trace_id=new_id,
            confidence=0.0,
            reasoned_fresh=True,
        )
```

- [ ] **Step 4: Run test to verify it passes**

Run: `pytest tests/test_engine.py -v`
Expected: PASS (5 passed)

- [ ] **Step 5: Commit**

```bash
git add src/coactra/ai/engine.py tests/test_engine.py
git commit -m "feat(ai): ReasoningEngine — capture/gate/bounded-retrieve/replay-or-fallback core"
```

---

### Task 9: Public surface + module-level convenience API

**Files:**
- Modify: `src/coactra/ai/__init__.py`
- Test: `tests/test_public_api.py`

Expose a flat, importable surface: `ask` and `structured` (the wrap shelf), plus the reasoning core as a class — `ReasoningEngine` with `capture` / `recall_or_reason` / `record_outcome` methods. (The charter README sketches `reasoning.capture(...)` as a namespace; we ship the same capability as engine methods — a deliberate, documented deviation, not a separate `reasoning` module. The public `__all__` below is the contract.)

- [ ] **Step 1: Write the failing test**

```python
# tests/test_public_api.py
import coactra.ai as ai


def test_public_exports_present():
    for name in [
        "ask",
        "structured",
        "ReasoningEngine",
        "ReasoningTrace",
        "Decision",
        "InMemoryStore",
        "AdaptiveGate",
        "LiteLLMEmbedding",
    ]:
        assert hasattr(ai, name), name


def test_engine_constructible_from_public_api():
    eng = ai.ReasoningEngine(
        store=ai.InMemoryStore(),
        embed=lambda t: [1.0, 0.0],
        reasoner=lambda p: "R",
    )
    tid = eng.capture("t", "prob", "reason")
    assert eng.store.get("t", tid).reasoning == "reason"
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/test_public_api.py -v`
Expected: FAIL with `AttributeError: module 'coactra.ai' has no attribute 'ask'`

- [ ] **Step 3: Write minimal implementation**

```python
# src/coactra/ai/__init__.py
"""coactra.ai — model-call shelf + reasoning capture-replay.

    import coactra.ai as ai
    ai.ask("hi")                       # call any model (LiteLLM)
    ai.structured(Schema, "...")       # typed output (Instructor)
    eng = ai.ReasoningEngine(store=ai.InMemoryStore(),
                             embed=ai.LiteLLMEmbedding(),
                             reasoner=lambda p: ai.ask(p))
    eng.recall_or_reason("tenant", problem)   # replay or re-reason
"""
from coactra.ai.client import LiteLLMCompleter, ask, structured
from coactra.ai.embedding import LiteLLMEmbedding, cosine
from coactra.ai.engine import ReasoningEngine
from coactra.ai.gate import AdaptiveGate
from coactra.ai.models import Decision, ReasoningTrace, RecallResult
from coactra.ai.store import InMemoryStore

__all__ = [
    "ask",
    "structured",
    "LiteLLMCompleter",
    "LiteLLMEmbedding",
    "cosine",
    "ReasoningEngine",
    "AdaptiveGate",
    "InMemoryStore",
    "ReasoningTrace",
    "RecallResult",
    "Decision",
]
```

- [ ] **Step 4: Run test to verify it passes**

Run: `pytest tests/test_public_api.py -v`
Expected: PASS (2 passed)

- [ ] **Step 5: Commit**

```bash
git add src/coactra/ai/__init__.py tests/test_public_api.py
git commit -m "feat(ai): public API surface (ask/structured/ReasoningEngine + defaults)"
```

---

### Task 10: Optional Chroma adapter (stub) + full suite green

**Files:**
- Create: `src/coactra/ai/adapters/__init__.py`
- Create: `src/coactra/ai/adapters/chroma.py`
- Test: `tests/test_chroma_adapter.py`

YAGNI: Protocol + one default (InMemoryStore) is the working backend. Chroma is a stub for the `[chroma]` extra — it must fail loudly if `chromadb` is absent, never silently.

> **Implementer note (latent issues in the stub, only matter once `[chroma]` is exercised live):** Chroma metadata values must be scalars, so `ReasoningTrace.meta` (a nested dict) cannot go straight into `metadatas` — flatten/JSON-encode it on `put` and decode on read. And Chroma's `query()` returns embeddings only when `include=["embeddings", "metadatas"]` is passed. These do not block the default path (the test below only asserts fail-loud + Protocol shape), but fix them before any real Chroma round-trip.

- [ ] **Step 1: Write the failing test**

```python
# tests/test_chroma_adapter.py
import pytest

from coactra.ai.adapters.chroma import ChromaStore


def test_chroma_store_requires_extra():
    # chromadb not installed in the dev env -> constructing must raise clearly.
    with pytest.raises(ImportError, match="chromadb"):
        ChromaStore(collection="reasoning")


def test_chroma_store_is_a_reasoning_store_type():
    from coactra.ai.protocols import ReasoningStore

    # The class declares the Protocol methods even though it needs the extra.
    for method in ("put", "search", "get"):
        assert hasattr(ChromaStore, method)
    assert hasattr(ReasoningStore, "__subclasshook__")
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/test_chroma_adapter.py -v`
Expected: FAIL with `ModuleNotFoundError: No module named 'coactra.ai.adapters'`

- [ ] **Step 3: Write minimal implementation**

```python
# src/coactra/ai/adapters/__init__.py
"""Optional backend adapters (extras). The default backend is InMemoryStore."""
```

```python
# src/coactra/ai/adapters/chroma.py
"""Optional ChromaStore adapter — install with `pip install coactra-ai[chroma]`.

Stub: implements the ReasoningStore Protocol shape over a Chroma collection.
Construction fails loudly if chromadb is not installed.
"""
from __future__ import annotations

from typing import Any

from coactra.ai.embedding import cosine
from coactra.ai.models import ReasoningTrace


class ChromaStore:
    def __init__(self, collection: str = "reasoning", **client_kwargs: Any) -> None:
        try:
            import chromadb
        except ImportError as exc:  # pragma: no cover - exercised only without extra
            raise ImportError(
                "ChromaStore requires the 'chroma' extra: pip install coactra-ai[chroma]"
            ) from exc
        self._client = chromadb.Client(**client_kwargs)
        self._col = self._client.get_or_create_collection(collection)

    def put(self, tenant: str, trace: ReasoningTrace) -> None:
        self._col.upsert(
            ids=[f"{tenant}:{trace.id}"],
            embeddings=[trace.embedding],
            metadatas=[{"tenant": tenant, **trace.model_dump(exclude={"embedding"})}],
        )

    def get(self, tenant: str, trace_id: str) -> ReasoningTrace | None:
        res = self._col.get(ids=[f"{tenant}:{trace_id}"], include=["metadatas", "embeddings"])
        if not res["ids"]:
            return None
        meta = res["metadatas"][0]
        return ReasoningTrace(embedding=res["embeddings"][0], **{k: v for k, v in meta.items() if k != "tenant"})

    def search(
        self, tenant: str, vector: list[float], k: int, min_quality: float
    ) -> list[tuple[ReasoningTrace, float]]:
        res = self._col.query(query_embeddings=[vector], n_results=k * 4, where={"tenant": tenant})
        out: list[tuple[ReasoningTrace, float]] = []
        for meta, emb in zip(res["metadatas"][0], res["embeddings"][0]):
            t = ReasoningTrace(embedding=emb, **{k2: v for k2, v in meta.items() if k2 != "tenant"})
            if t.quality >= min_quality:
                out.append((t, cosine(vector, emb)))
        out.sort(key=lambda p: p[1], reverse=True)
        return out[:k]
```

- [ ] **Step 4: Run test to verify it passes**

Run: `pytest tests/test_chroma_adapter.py -v`
Expected: PASS (2 passed)

- [ ] **Step 5: Run the full suite + commit**

Run: `pytest -v`
Expected: PASS (all tests, ~28 passed)

```bash
git add src/coactra/ai/adapters tests/test_chroma_adapter.py
git commit -m "feat(ai): optional ChromaStore adapter stub (fails loudly without extra)"
```

---

## Self-Review

**Spec coverage:**
- WRAP shelf (LiteLLM routes + Instructor types) → Task 7 (`ask`, `structured`). ✓
- BUILD reasoning capture-replay → Tasks 3, 5, 6, 8. ✓
- Guardrail 1 adaptive/verified gate (not static) → Task 6, discriminating "boundary moves" test. ✓
- Guardrail 2 bounded + quality-filtered retrieval → Task 5 (`k` + `min_quality`). ✓
- Guardrail 3 explicit replay-vs-re-reason fallback → Task 8, three branches (A replay / B gate-reject re-reason / C no-candidate re-reason). ✓
- Wrap a vector store, default in-process cosine, chromadb optional adapter → Tasks 4/5 default, Task 10 stub. ✓
- Procedural-memory record → Task 3 `ReasoningTrace`. ✓
- Multi-tenant scoping first-class (threads through, real isolation) → `tenant` param everywhere; isolation tests in Tasks 5 and 8. ✓
- Outcome-feedback seam unifying gate + quality filter → Task 3 `quality`, Task 8 `record_outcome`. ✓
- Protocol + ONE default each (no half-built/dead Protocols) → Task 2: `EmbeddingFn`→`LiteLLMEmbedding`, `Completer`→`LiteLLMCompleter`, `ReasoningStore`→`InMemoryStore`. `ChromaStore` is the optional extra adapter behind `[chroma]`. ✓
- PEP 420 namespace, src layout, py.typed, hatchling, optional-deps, 3.12+, pytest → Task 1. ✓
- deps limited to instructor/litellm/pydantic/numpy → pyproject Task 1. ✓
- README not overwritten → no task touches it. ✓

**Placeholder scan:** No "TBD"/"add error handling"/"similar to Task N". Every code step has real code. ✓

**Type consistency:** `ReasoningTrace`, `Decision`, `RecallResult`, `AdaptiveGate.required/accept/confidence`, `InMemoryStore.put/get/search`, `ReasoningEngine.capture/recall_or_reason/record_outcome`, `Completer.complete`, `EmbeddingFn.__call__` — names identical across Tasks 2→10. `min_quality`/`k` thread consistently from store (Task 5) into engine (Task 8). ✓

**Deliberately deferred:** live-model integration tests (all unit tests inject fakes, zero network); retries/streaming on the wrap shelf; a real (non-stub) Chroma round-trip; FAISS/persistent stores; embedding caching. The Protocol seams make each a later swap, not a rewrite.
