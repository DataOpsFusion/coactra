# Work Examples

Focused scripts for the durable work API.

```bash
python3 examples/work/release_work_lifecycle.py
python3 examples/work/change_approval_gate.py
python3 examples/work/procedure_runbook.py
```

| File | Shows |
|---|---|
| `release_work_lifecycle.py` | submit, claim, start, checkpoint, complete, audit events |
| `change_approval_gate.py` | blocked work, human decision, resume, completion artifact |
| `procedure_runbook.py` | `Orchestrator` + registered `Procedure` |

For a project layout, see [../projects/release_checkpoint](../projects/release_checkpoint).
