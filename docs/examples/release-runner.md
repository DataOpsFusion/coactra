# Release Runner

Use this when your app needs durable work state instead of a one-shot function
call.

## Demonstrates

- `WorkManager`
- idempotent `WorkOrder` submission
- leases and checkpoints
- completion artifacts
- audit event history

## Run

```bash
python3 examples/projects/release_runner/app.py
```

## Production Swap

```python
from coactra.jobs import SqlWorkStore, WorkManager

work = WorkManager(store=SqlWorkStore.from_url("postgresql+psycopg://..."))
```

Source: [https://github.com/DataOpsFusion/coactra/tree/main/examples/projects/release_runner](https://github.com/DataOpsFusion/coactra/tree/main/examples/projects/release_runner)
