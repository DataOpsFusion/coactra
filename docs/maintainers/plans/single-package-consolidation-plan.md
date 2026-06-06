# Single-Package Consolidation Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Collapse the 7 Coactra distributions into one `coactra` distribution with per-capability extras, and unify the duplicated `Scope` / `TenantRouter` / errors / base-ports into a single source of truth.

**Architecture:** This is a brownfield **refactor**, not new behaviour. The `coactra/` package is already a real package (`src/coactra/{scope,errors,kernel,plugins}.py`); we move the other six `src/coactra/*` trees into it and merge their `pyproject.toml` deps into one with extras. Verification at each step is **the existing per-package test suites stay green** (there is almost no new code), plus one new base-import test. Each step is its own commit so any one is revertible.

**Tech Stack:** Python 3.12, hatchling, pydantic, uv, pytest (run via the repo venv `/home/developer/mcp/library/.venv/bin/python` — system python is PEP-668 externally-managed).

**Spec:** `docs/superpowers/specs/2026-06-05-single-package-consolidation-design.md`. **Branch:** do this on `chore/consolidate-package` off `main` (this is a large structural change; keep `main` clean until it's verified end-to-end).

**Ground truth (verified 2026-06-05):**
- Canonical namespaces are `coactra.jobs` (was orchestration) and `coactra.directory` (was organization). `coactra.orchestration` / `coactra.work` / `coactra.workflow` / `coactra.organization` are **compat-shim packages** that re-export the canonical ones. **Keep all shims** — homelab-mcp imports `coactra.orchestration.*` through them.
- Six `Scope` definitions: `agent/src/coactra/agent/domain/scope.py`, `memory/src/coactra/memory/types.py`, `workspace/src/coactra/workspace/scope.py`, `jobs/src/coactra/jobs/work/domain/scope.py`, `jobs/src/coactra/jobs/workflow/domain/scope.py`, plus the canonical `coactra/src/coactra/scope.py::CoactraScope`.
- The generic router is `coactra.jobs._tenant_router::TenantRouter[T]`. Bespoke routers: `lib-ai/.../ai/routing.py`, `memory/.../memory/routing.py`, `workspace/.../workspace/routing.py`, `directory/.../directory/repository/routing.py`, `agent/.../agent/routing.py`.

---

## File structure (target, after Task 1)

```
coactra/                         # the ONE distribution
  pyproject.toml                 # base = pydantic only; one [project.optional-dependencies] block (extras)
  README.md
  src/coactra/                   # one tree, PEP 420 namespace (no top-level __init__.py)
    scope.py errors.py kernel.py plugins.py ports.py _routing.py   # shared core (single source of truth)
    ai/ memory/ workspace/ agent/
    jobs/ directory/             # canonical
    orchestration/ work/ workflow/ organization/   # compat shims (re-export canonical)
  tests/                         # merged: tests/<capability>/...
lib-ai/ memory/ workspace/ jobs/ directory/ agent/   # DELETED after Task 1 (dirs emptied + pyprojects removed)
```

`homelab-mcp` later swaps its 6 `coactra-*` path deps for one `coactra` path dep (Task 6); its imports are untouched.

---

## Task 0: Branch

- [ ] **Step 1: Create the work branch**

Run: `cd /home/developer/mcp/library && git checkout -b chore/consolidate-package && git branch --show-current`
Expected: `chore/consolidate-package`, tree clean.

---

## Task 1: Merge the six trees into the `coactra` package (mechanical)

**Files:** move `*/src/coactra/*` into `coactra/src/coactra/`; merge `*/pyproject.toml` extras into `coactra/pyproject.toml`; merge `*/tests` into `coactra/tests/`; delete the 6 package dirs.

- [ ] **Step 1: Move the source trees** (namespaces are disjoint subdirs, so no file collisions)

```bash
cd /home/developer/mcp/library
git mv lib-ai/src/coactra/ai                 coactra/src/coactra/ai
git mv memory/src/coactra/memory             coactra/src/coactra/memory
git mv workspace/src/coactra/workspace       coactra/src/coactra/workspace
git mv agent/src/coactra/agent               coactra/src/coactra/agent
git mv jobs/src/coactra/jobs                 coactra/src/coactra/jobs
git mv jobs/src/coactra/orchestration        coactra/src/coactra/orchestration
git mv jobs/src/coactra/work                 coactra/src/coactra/work
git mv jobs/src/coactra/workflow             coactra/src/coactra/workflow
git mv directory/src/coactra/directory       coactra/src/coactra/directory
git mv directory/src/coactra/organization    coactra/src/coactra/organization
```

- [ ] **Step 2: Move the tests** into one tree

```bash
cd /home/developer/mcp/library
for p in lib-ai memory workspace agent jobs directory; do
  mkdir -p "coactra/tests/$p"
  git mv "$p"/tests/* "coactra/tests/$p"/ 2>/dev/null || true
done
```
If any package has a `tests/conftest.py` adding `src` to `sys.path`, it is now redundant (one `src` tree) — leave it; it is harmless. If two `conftest.py` define the same fixture name and collide at collection, namespace them under their `coactra/tests/<p>/` subdir (they already are).

- [ ] **Step 3: Merge dependencies into `coactra/pyproject.toml`**

Read each old `*/pyproject.toml`'s `dependencies` and `optional-dependencies`, then write a single `coactra/pyproject.toml`. Base `dependencies = ["pydantic>=2.7"]`. Add one `[project.optional-dependencies]` block following the spec §5 scheme (ai/memory/work/workflow/orchestration/organization/agent/oauth/all; **no** daytona/e2b/openhands/mcp/neo4j — those stubs were removed). Keep `[tool.hatch.build.targets.wheel] packages = ["src/coactra"]` and the sdist block. Remove every `[tool.uv.sources]` sibling-path entry (no siblings anymore). Keep `requires-python`, classifiers, urls (`github.com/DataOpsFusion/coactra`).

- [ ] **Step 4: Delete the now-empty package dirs**

```bash
cd /home/developer/mcp/library
git rm -r lib-ai memory workspace agent jobs directory
```
(Each is now just an emptied `src/` + its old `pyproject.toml`/`README.md`/`uv.lock` — all superseded by the single package.)

- [ ] **Step 5: Point the venv at the one package and install it editable**

```bash
VP=/home/developer/mcp/library/.venv/bin/python
$VP -m pip install -e '/home/developer/mcp/library/coactra[all]'
```
Expected: installs without error (resolves all real backends; this is the proof the merged pyproject is valid).

- [ ] **Step 6: Run the whole suite — must stay green**

```bash
cd /home/developer/mcp/library/coactra && /home/developer/mcp/library/.venv/bin/python -m pytest -q
```
Expected: the sum of the previous per-package passes (≈ 470+ passed, some skipped), **0 failures, 0 errors**. If there are import errors, they will name a stale path — fix the offending import to the merged location, re-run. Do not proceed until green.

- [ ] **Step 7: Update `Makefile` + CI to the single package**

`Makefile`: replace the per-package loops with `test: cd coactra && python3 -m pytest -q`. `.github/workflows/ci.yml`: replace the multiple `pip install -e './<pkg>[dev]'` steps with one `pip install -e './coactra[all,dev]'` then `cd coactra && pytest -q`.

- [ ] **Step 8: Commit**

```bash
git add -A && git commit -m "refactor: merge the 6 capability packages into the single coactra package"
```

---

## Task 2: Add the base-import test (pins the extras contract)

**Files:** Create `coactra/tests/test_base_install.py`.

- [ ] **Step 1: Write the test**

```python
# coactra/tests/test_base_install.py
"""Base install imports every capability's pure-Python core; heavy backends are gated."""
import importlib
import pytest

CAPABILITY_ROOTS = [
    "coactra.ai", "coactra.memory", "coactra.workspace",
    "coactra.jobs", "coactra.jobs.work", "coactra.jobs.workflow",
    "coactra.directory", "coactra.agent", "coactra.scope", "coactra.errors",
]

@pytest.mark.parametrize("mod", CAPABILITY_ROOTS)
def test_capability_core_imports(mod):
    importlib.import_module(mod)  # must import with base deps (pydantic) alone

def test_compat_shims_still_resolve():
    for mod in ("coactra.orchestration", "coactra.work", "coactra.workflow", "coactra.organization"):
        importlib.import_module(mod)
```

- [ ] **Step 2: Run it**

Run: `cd coactra && /home/developer/mcp/library/.venv/bin/python -m pytest tests/test_base_install.py -q`
Expected: PASS. (If a capability root fails to import with the full `[all]` env, that's fine here; the strict base-only check is exercised in CI with a minimal env — note that in the test docstring and CI.)

- [ ] **Step 3: Commit**

```bash
git add coactra/tests/test_base_install.py && git commit -m "test: base-install imports + compat-shim resolution"
```

---

## Task 3: Unify `Scope` (the one design-judgment step)

**Files:** `coactra/src/coactra/scope.py` (canonical), the 5 per-capability scope modules, their importers.

Approach: `coactra.scope` already holds `CoactraScope` (fields `tenant_id`, `namespace`, `agent_id?`, `session_id?` + validation + conversion methods). Promote it to the single `Scope`. Each capability's `Scope` becomes a **thin subclass/alias** of `coactra.scope.Scope` exposing the field names that capability already used, so existing call-sites and tests keep working; mark the per-capability ones deprecated.

- [ ] **Step 1: Make `coactra.scope.Scope` the canonical name**

In `coactra/src/coactra/scope.py`, add `Scope = CoactraScope` (keep `CoactraScope` as a documented alias) and add `Scope` to `__all__`. Keep all existing methods.

- [ ] **Step 2: Repoint ONE capability first (memory — it has the widest fields) and prove the pattern**

`coactra/src/coactra/memory/types.py`: replace the standalone `class Scope(BaseModel)` body with a thin wrapper that derives from the canonical fields, preserving memory's existing `tenant`/`namespace`/`agent`/`session` accessors and its `group_id` key. Keep the class name `Scope` and its public attributes identical (so memory's tests don't change).

```python
# pattern (adapt field names to memory's existing API):
from coactra.scope import Scope as _CanonicalScope
# keep memory.Scope's existing public surface; internally map to the canonical fields.
```

- [ ] **Step 3: Run memory's tests**

Run: `cd coactra && /home/developer/mcp/library/.venv/bin/python -m pytest tests/memory -q`
Expected: PASS unchanged. If a memory test asserts a field name, keep that field on the wrapper. Iterate until green.

- [ ] **Step 4: Repeat Steps 2–3 for `agent`, `workspace`, `jobs.work`, `jobs.workflow`**

For each, replace the local `Scope` with a thin wrapper over `coactra.scope.Scope` preserving that capability's exact public attributes, and run that capability's tests (`pytest tests/<cap> -q`) green before moving on.

- [ ] **Step 5: Convert `CoactraScope` consumers + run full suite**

Anything importing `CoactraScope` keeps working (it's an alias). Run the full suite green: `cd coactra && .venv-python -m pytest -q`.

- [ ] **Step 6: Commit**

```bash
git add -A && git commit -m "refactor(scope): single canonical coactra.scope.Scope; per-capability Scopes wrap it"
```

---

## Task 4: Unify `TenantRouter`

**Files:** `coactra/src/coactra/_routing.py` (new home for the generic), `coactra/src/coactra/jobs/_tenant_router.py` (becomes a re-export), the 5 bespoke routers.

- [ ] **Step 1: Move the generic to the shared root**

`git mv coactra/src/coactra/jobs/_tenant_router.py coactra/src/coactra/_routing.py`. In `coactra/src/coactra/jobs/_tenant_router.py` (recreate as a 2-line shim) `from coactra._routing import TenantRouter` so `coactra.jobs._tenant_router.TenantRouter` still resolves.

- [ ] **Step 2: Run jobs tests**

Run: `cd coactra && .venv-python -m pytest tests/jobs -q` → PASS.

- [ ] **Step 3: Reimplement each bespoke router on the generic, one at a time**

For `ai/routing.py`, `memory/routing.py`, `workspace/routing.py`, `directory/repository/routing.py`, `agent/routing.py`: replace the hand-rolled cache/dispatch with a subclass/instantiation of `coactra._routing.TenantRouter[<BackendType>]`, preserving the class name and public method signatures. After EACH, run that capability's tests green.

- [ ] **Step 4: (optional, spec §6.2) add bounded-cache eviction to the generic** + a test asserting eviction; run full suite.

- [ ] **Step 5: Commit**

```bash
git add -A && git commit -m "refactor(routing): single generic TenantRouter[T]; per-capability routers wrap it"
```

---

## Task 5: Consolidate errors / base ports

**Files:** `coactra/src/coactra/errors.py` (already exists), `coactra/src/coactra/ports.py` (new, if a shared marker is warranted).

- [ ] **Step 1: Inventory error types** — `grep -rn "class .*Error" coactra/src/coactra --include="*.py" | grep -v tests`. Move genuinely-shared ones (e.g. `MissingExtraError`, a base `CoactraError`) into `coactra/src/coactra/errors.py`; in their old location leave `from coactra.errors import X` re-exports so existing imports keep working.
- [ ] **Step 2: Run full suite** green after each move.
- [ ] **Step 3: Ports** — only create `coactra/src/coactra/ports.py` if ≥2 capabilities share an identical base Protocol marker today (rule of three). If not, skip (YAGNI).
- [ ] **Step 4: Commit** `git commit -am "refactor(errors): shared error types in coactra.errors"`.

---

## Task 6: Swap the consumer (homelab-mcp) + build/publish docs

**Files:** `/home/developer/mcp/homelab-mcp/agent/pyproject.toml` (+ any other pyproject with `coactra-*` path sources), `coactra/pyproject.toml`, `docs/`.

- [ ] **Step 1: Replace homelab-mcp's 6 path deps with one**

In `homelab-mcp/agent/pyproject.toml`, replace the six `coactra-* = { path = "../../library/<pkg>", editable = true }` `[tool.uv.sources]` entries and the six `coactra-*>=...` requirements with a single `coactra = { path = "../../library/coactra", editable = true }` source and one `coactra[ai,memory,workspace,orchestration,organization,agent]` (or `[all]`) requirement. Its `from coactra.* import ...` lines do **not** change.

- [ ] **Step 2: Verify homelab-mcp resolves + imports**

Run (homelab-mcp's env): `cd /home/developer/mcp/homelab-mcp && <its python> -c "import coactra.orchestration.work, coactra.agent, coactra.memory; print('ok')"` and its package tests for any changed package. Expected: ok / green. (The compat shims make the old `coactra.orchestration.*` imports resolve.)

- [ ] **Step 3: Build + validate the one distribution**

```bash
cd /home/developer/mcp/library && rm -rf dist-all && (cd coactra && uv build --out-dir ../dist-all) && uvx twine check dist-all/*
```
Expected: one sdist + one wheel, both PASS.

- [ ] **Step 4: Update docs** — `docs/concepts/library-map.md` (one package + extras, not 7), `docs/PUBLISHING.md` + `.github/workflows/release.yml` (build/publish ONE distribution), `README.md`/`docs/getting-started/quickstart.md` install lines (`pip install "coactra[...]"`), `CHANGELOG.md` (Added: single-package layout; Changed: install via extras). Reconcile the moved-doc cross-links from the earlier cleanup (CHANGELOG/CONTRIBUTING → `docs/maintainers/release-policy.md`).

- [ ] **Step 5: Commit**

```bash
git add -A && git commit -m "refactor: one coactra distribution — update consumer, build, and docs"
```

---

## Done-criteria

- `cd coactra && .venv-python -m pytest -q` → all prior tests pass, 0 failures/errors, + the base-install test.
- `coactra/` is the only package dir with a `pyproject.toml` under `library/`; the 6 old package dirs are gone.
- Old imports (`coactra.orchestration.*`, `coactra.organization`) AND canonical (`coactra.jobs.*`, `coactra.directory`) both resolve.
- `Scope` is defined once (`coactra.scope.Scope`); `TenantRouter` once (`coactra._routing`).
- `uv build` → one sdist + wheel; `twine check` PASS.
- homelab-mcp resolves against the single `coactra` dep and imports cleanly.

## Notes

- This is a refactor: the safety net is the **existing suites staying green at every commit**, not new tests. Run them via the repo venv after every step; never advance on red.
- Keep every compat shim (`coactra.orchestration/work/workflow/organization`) — the consumer depends on them. Removing shims is a *separate*, later, deprecation-windowed decision.
- Merge `chore/consolidate-package` → `main` only after the full suite + homelab-mcp verify green.
