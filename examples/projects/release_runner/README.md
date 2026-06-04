# Release Runner

Use this when your app needs durable work state instead of a one-shot function call.

What it demonstrates:

- `WorkManager`
- idempotent `WorkOrder` submission
- leases and checkpoints
- completion artifacts
- audit event history

Run from the repo root:

```bash
PYTHONPATH=orchestration/src python3 examples/projects/release_runner/app.py
```

Production swap:

```python
from coactra.orchestration.work import SqlWorkStore, WorkManager

work = WorkManager(store=SqlWorkStore.from_url("postgresql+psycopg://..."))
```
