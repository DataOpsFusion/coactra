# Procedure-Backed Work

Use this when a work order should follow a registered procedure recipe instead of
ad-hoc handler code.

## Demonstrates

- `Orchestrator` joining the work ledger and procedure store
- registering a `Procedure` with `Step` definitions
- submitting a `WorkOrder` that names a procedure
- running to completion with audit state on the order

## Run

```bash
python3 examples/work/procedure_backed_work.py
```

## When To Use Which API

| Need | API |
|---|---|
| Durable job lifecycle only | `WorkManager` |
| Job + reusable recipe | `Orchestrator` + `Procedure` |
| LangGraph / Temporal durability | `DurableOrchestrator` + workflow engine adapter |

## Import Paths

Prefer canonical namespaces:

```python
from coactra.jobs import Orchestrator, Procedure, Step, WorkOrder, WorkScope
```

Legacy `coactra.orchestration` imports still resolve but are deprecated.
