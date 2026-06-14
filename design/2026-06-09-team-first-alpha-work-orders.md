# Team-First Alpha Refactor Work Orders

Status: planning document for the single alpha-breaking PR
Date: 2026-06-09

## Objective

Execute the agreed Team-first Coactra target architecture in one coordinated alpha-breaking pass:

- Team is the public assembly and execution door
- Policy is explicit and required
- Workflow routing uses `requires_skill`, not `needs`
- Model selection goes through a governed `ModelResolver`
- `Agent.create()` is removed
- Docs, examples, and tests are rewritten in the same PR

This document is organized as implementation work orders with exact production files, exact test fallout, and the required execution order.

## Locked execution order

1. Team spine
2. Team-owned agent assembly
3. Workflow routing rewrite (`requires_skill`)
4. Model resolver seam
5. Delete `Agent.create()`
6. Docs/examples rewrite
7. Test rewrite sweep
8. Broader verification and fallout fixes

Do not invert this order. In particular, do not delete `Agent.create()` before the Team-owned replacement path and `requires_skill` workflow routing are working.

## Work Order 1: Team Spine

Goal: make `Team` the canonical assembly/runtime root before any old entrypoint is removed.

### Production files

- `coactra/src/coactra/team/facade.py`
- `coactra/src/coactra/team/__init__.py`
- `coactra/src/coactra/__init__.py`
- `coactra/src/coactra/policy.py`

### Required changes

- Replace the current lean `Team(members, match=..., policy=...)` shape with a Team-first constructor.
- Require explicit `policy`.
- Add Team-owned:
  - `scope`
  - agent catalog
  - skill catalog
  - workflow catalog
  - runtime cache
- Add methods:
  - `add_agent(...)`
  - `add_skill(...)`
  - `assign_skill(...)`
  - `add_workflow(...)`
  - `match_skill(...)`
  - `run(...)`
- Keep Team facade dependency-light.
- Keep deep directory APIs under `coactra.team.directory` only.

### Canonical state rule

- Canonical state should be agent specifications and catalogs.
- Live `Agent` runtime instances should be cached/generated, not canonical.

### Tests to rewrite first

- `coactra/tests/agent/test_team.py`
- `coactra/tests/team/test_public_api.py`
- `coactra/tests/test_docs_imports.py`
- `coactra/tests/test_base_install.py`

### Acceptance criteria

- `Team` cannot be created without explicit `policy`.
- `Team.add_agent(...)` exists.
- `Team.add_skill(...)` and `Team.add_workflow(...)` exist.
- `coactra.team` exports the Team facade only.
- Root `coactra` import path remains light.

## Work Order 2: Team-Owned Agent Assembly

Goal: move agent construction responsibility under Team while preserving current runtime behavior.

### Production files

- `coactra/src/coactra/agent/facade.py`
- `coactra/src/coactra/agent/runtime.py`
- `coactra/src/coactra/agent/runtime_wiring.py`
- `coactra/src/coactra/agent/bindings.py`
- `coactra/src/coactra/agent/skills.py`
- `coactra/src/coactra/agent/peers.py`
- `coactra/src/coactra/team/facade.py`

### Required changes

- Extract the current assembly logic out of `Agent.create()` into Team-owned construction helpers.
- `Team.add_agent(...)` must own:
  - model/runtime binding
  - memory binding
  - workspace binding
  - MCP gateway wiring
  - peer wiring
  - learned procedure wiring
  - agent card capability publication inputs
- `Agent` remains the runtime type returned by Team.
- `Agent.create()` may temporarily delegate internally during the refactor, but it is not the target API.

### Tests to rewrite

- `coactra/tests/agent/test_facade.py`
- `coactra/tests/agent/test_toplevel.py`
- `coactra/tests/agent/test_facade_peers.py`
- `coactra/tests/agent/test_memory.py`
- `coactra/tests/agent/test_gateway.py`
- `coactra/tests/agent/test_registry.py`
- `coactra/tests/agent/test_learned_procedures.py`
- `coactra/tests/agent/test_tracing.py`
- `coactra/tests/agent/test_integration.py`
- `coactra/tests/agent/test_acceptance_live.py`
- `coactra/tests/agent/test_live_zen_agent.py`

### Acceptance criteria

- Team can construct a working runtime agent.
- Peer tools, memory, workspace, and gateway behavior still work through Team-owned construction.
- Runtime `agent.run(...)` behavior is preserved.

## Work Order 3: Workflow Routing Rewrite (`requires_skill`)

Goal: replace free-text `needs` with explicit skill requirements.

### Production files

- `coactra/src/coactra/workflow/playbook.py`
- `coactra/src/coactra/agent/workflow.py`
- `coactra/src/coactra/agent/planner.py`
- `coactra/src/coactra/agent/matcher.py`
- `coactra/src/coactra/team/facade.py`

### Required changes

- Remove `Step.needs`.
- Add `Step.requires_skill`.
- Update `step(...)` helper.
- Keep `agent=` pin as override.
- Change workflow dispatch from `team.match(needs)` to `team.match_skill(requires_skill)`.
- Planner prompt and planner schema must emit `requires_skill`.
- Playbook dict/YAML serialization must emit `requires_skill`.

### Tests to rewrite

- `coactra/tests/agent/test_workflow.py`
- `coactra/tests/agent/test_workflow_goal.py`
- `coactra/tests/agent/test_planner.py`
- `coactra/tests/agent/test_playbook_store.py`
- `coactra/tests/agent/test_checkpoint.py`
- `coactra/tests/agent/test_tracing.py`
- `coactra/tests/workflow/runtime/test_workflow_models.py`
- `coactra/tests/workflow/runtime/test_workflow_public_api.py`
- `coactra/tests/workflow/runtime/test_workflow_scope.py`

### Acceptance criteria

- `requires_skill` is the only public skill-routing field.
- Planner produces skill identifiers, not free-text `needs`.
- Workflow routing succeeds through Team skill matching.
- Unmatched required skill fails cleanly.

## Work Order 4: Model Resolver Seam

Goal: make model routing governed and Team-owned.

### New production area

- `coactra/src/coactra/model/`

### Expected files

- `coactra/src/coactra/model/__init__.py`
- `coactra/src/coactra/model/models.py`
- `coactra/src/coactra/model/resolver.py`
- optional adapter module for LiteLLM route translation

### Existing files to touch

- `coactra/src/coactra/agent/runtime.py`
- `coactra/src/coactra/team/facade.py`
- `coactra/src/coactra/policy.py`

### Required changes

- Add:
  - `ModelProfile`
  - `ModelRoute`
  - `ModelResolver`
- Prefer `model_capability=` in `Team.add_agent(...)`.
- Consult `Policy` before route selection.
- Add LiteLLM route mapping seam.
- Keep temporary alpha escape hatch:
  - `Team.add_agent(model=<pydantic_ai_model>)`
- Do not restore `litellm_model.py`.

### Tests to rewrite/add

- `coactra/tests/ai/test_models.py`
- `coactra/tests/ai/test_routing.py`
- `coactra/tests/agent/test_runtime.py`
- `coactra/tests/agent/test_gateway.py`
- `coactra/tests/agent/test_live_zen_agent.py`
- `coactra/tests/ai/test_public_api.py`

### Acceptance criteria

- Capability resolves to route.
- Policy can deny route selection.
- Raw pydantic-ai model escape hatch still works during the refactor.
- Route metadata is available to runtime/planner when needed.

## Work Order 5: Delete `Agent.create()`

Goal: remove the old public construction path only after the replacement path is real.

### Production files

- `coactra/src/coactra/agent/facade.py`
- `coactra/src/coactra/agent/__init__.py`
- `coactra/src/coactra/__init__.py`

### Required changes

- Remove `Agent.create()`.
- Keep runtime methods:
  - `run()`
  - `send()`
  - `aclose()`
- Keep `Agent` as public runtime noun.
- Make Team-first narrative explicit in root exports and docs.

### Tests to rewrite

- `coactra/tests/agent/test_public_api.py`
- `coactra/tests/test_docs_imports.py`
- `coactra/tests/test_base_install.py`
- all remaining `Agent.create()` references in `coactra/tests/agent/`

### Acceptance criteria

- `Agent.create` is absent.
- No compat aliases.
- Team-first root API is the documented public assembly path.

## Work Order 6: Policy Propagation

Goal: make Team policy canonical across agent, workflow, memory, workspace, and delegation boundaries.

### Production files

- `coactra/src/coactra/team/facade.py`
- `coactra/src/coactra/agent/collaboration.py`
- `coactra/src/coactra/workspace/policy.py`
- `coactra/src/coactra/memory/authorization.py`
- `coactra/src/coactra/agent/runtime.py`
- `coactra/src/coactra/agent/workflow.py`

### Required changes

- Team owns canonical policy.
- Team-created agents consume Team policy unless explicitly overridden.
- Remove implicit Team-level same-tenant behavior as a construction default.
- Low-level helpers like `AllowSameTenant` may remain as explicit building blocks, but Team must not invent policy implicitly.
- Ensure model/tool/memory/workflow/delegation paths consult Policy.

### Tests to rewrite

- `coactra/tests/agent/test_collaboration.py`
- `coactra/tests/workspace/test_policy.py`
- `coactra/tests/memory/test_authorization.py`
- `coactra/tests/test_policy.py`
- `coactra/tests/agent/test_team.py`

### Acceptance criteria

- Team without policy is invalid.
- Permissive behavior is always explicit.
- Policy participation is visible in model, workspace, memory, workflow, and delegation paths.

## Work Order 7: Agent Card and Effective Capability Publication

Goal: keep effective capability advertising aligned with Team-owned skill assignment.

### Production files

- `coactra/src/coactra/agent/skills.py`
- `coactra/src/coactra/agent/facade.py`
- `coactra/src/coactra/agent/peers.py`

### Required changes

- Cards must advertise effective skills assigned through Team.
- No raw team catalog leakage.
- If card representation changes from plain dict to SDK type, do it here.

### Tests to rewrite

- `coactra/tests/agent/test_skills.py`
- `coactra/tests/agent/test_team.py`
- `coactra/tests/agent/test_peers.py`

### Acceptance criteria

- Agent cards remain curated and safe.
- Effective skill publication reflects Team-owned assignment.

## Work Order 8: Documentation Rewrite

Goal: remove the Agent-first and `needs`-based narrative from public docs.

### Top priority docs

- `README.md`
- `docs/API_INDEX.md`
- `docs/getting-started/quickstart.md`
- `docs/getting-started/bring-your-own.md`
- `docs/examples/index.md`
- `docs/maintainers/target-architecture.md`
- `docs/maintainers/roadmap.md`
- `docs/maintainers/agent-design.md`
- `docs/maintainers/memory-design.md`

### Docs with explicit `Agent.create()` or `needs`

- `docs/examples/support-desk.md`
- `docs/examples/release-runner.md`
- `docs/examples/workspace-research-desk.md`
- `docs/examples/multi-agent-policy.md`
- `docs/examples/offline-agent-sdk.md`
- `docs/examples/procedure-backed-work.md`
- `docs/examples/customer-support-memory.md`
- `docs/examples/composed-support-agent.md`
- `docs/examples/work-order-lifecycle.md`
- `docs/examples/basic-incident-triage.md`

### Rewrite rules

- no `Agent.create()`
- no `needs`
- no implicit Team policy
- Team-first examples
- `requires_skill` in all workflow samples

## Work Order 9: Example Code Rewrite

Goal: keep runnable examples aligned with the new public path.

### Examples to rewrite

- `examples/incident_response_handoff.py`
- `examples/offline_sre_agent.py`
- `examples/support_ticket_agent.py`
- `examples/acceptance/bring_existing_model.py`
- `examples/acceptance/bring_existing_memory_workspace.py`
- `examples/acceptance/attach_mcp_toolset.py`
- `examples/projects/ticket_triage/app.py`

### Acceptance criteria

- Every example builds a Team.
- Agents are added through Team.
- Workflows use `requires_skill`.
- No example depends on `Agent.create()`.

## Work Order 10: Test Rewrite Sweep

Goal: rewrite the high-fallout tests after the production surface is stable.

### Must rewrite because of `Agent.create()`

- `coactra/tests/agent/test_facade.py`
- `coactra/tests/agent/test_toplevel.py`
- `coactra/tests/agent/test_gateway.py`
- `coactra/tests/agent/test_registry.py`
- `coactra/tests/agent/test_facade_peers.py`
- `coactra/tests/agent/test_live_zen_agent.py`
- `coactra/tests/agent/test_integration.py`
- `coactra/tests/agent/test_learned_procedures.py`
- `coactra/tests/agent/test_acceptance_live.py`

### Must rewrite because of `needs`

- `coactra/tests/agent/test_workflow.py`
- `coactra/tests/agent/test_workflow_goal.py`
- `coactra/tests/agent/test_planner.py`
- `coactra/tests/agent/test_playbook_store.py`
- `coactra/tests/agent/test_checkpoint.py`
- `coactra/tests/workflow/runtime/test_workflow_models.py`

### Must rewrite because Team semantics change

- `coactra/tests/agent/test_team.py`
- `coactra/tests/agent/test_peers.py`
- `coactra/tests/agent/test_collaboration.py`
- `coactra/tests/team/test_public_api.py`

### Must rewrite because public docs/imports change

- `coactra/tests/test_docs_imports.py`
- `coactra/tests/test_examples.py`
- `coactra/tests/test_base_install.py`

## Verification order

### Phase-local targeted verification

- Team/API:
  - `pytest tests/agent/test_team.py tests/team/test_public_api.py tests/test_docs_imports.py`
- Workflow/planner:
  - `pytest tests/agent/test_workflow.py tests/agent/test_workflow_goal.py tests/agent/test_planner.py`
- Agent/runtime/model:
  - `pytest tests/agent/test_runtime.py tests/agent/test_gateway.py tests/agent/test_facade_peers.py`

### Broader verification

- `make test`
- `make compile`

## Notes for execution

- The current repo is still deeply Agent-first and `needs`-based; this is expected fallout, not a sign the target is wrong.
- Deleting `Agent.create()` early is the main avoidable failure mode.
- `requires_skill` should be treated as a hard rename, not an alias.
- `Team.add_agent(model=...)` may exist temporarily as an alpha escape hatch while `ModelResolver` lands, but `model_capability=` is the target path.
