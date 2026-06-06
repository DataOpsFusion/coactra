# Work Examples

Runnable scripts for `coactra.jobs` — durable work orders, leases, checkpoints,
approvals, and procedure-backed execution.

Install once from the repository root:

```bash
python -m pip install -e "./coactra[dev]"
```

Run any example:

```bash
python3 examples/work/submit_and_complete.py
python3 examples/work/lifecycle_with_approval.py
python3 examples/work/procedure_backed_work.py
```

| Script | Shows |
|---|---|
| `submit_and_complete.py` | Submit, claim, checkpoint, complete, audit events |
| `lifecycle_with_approval.py` | Pause, approval gate, resume, artifact |
| `procedure_backed_work.py` | `Orchestrator` + registered `Procedure` |

For a small project layout, see [../projects/release_runner](../projects/release_runner).

**Import style:** prefer `from coactra.jobs import Scope, WorkManager, WorkOrder`.
Legacy `coactra.orchestration` / `coactra.work` shims still resolve but are deprecated.
