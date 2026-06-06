# Support Desk

Use this when a helpdesk app needs agent drafting, durable work state, and ticket
memory in one place.

## Demonstrates

- `make_agent(...)` with dependency-light defaults
- `WorkManager` lifecycle and completion artifacts
- `Memory.remember` / `Memory.recall` for prior fixes
- canonical imports across agent, jobs, and memory

## Run

```bash
python3 examples/projects/support_desk/app.py
```

The default agent uses an in-process fake model. Wire a real model for production
drafts.

## Production Swap

```python
memory = Memory(backend=make_backend("graphiti", ...))
work = WorkManager(store=SqlWorkStore.from_url("postgresql+psycopg://..."))
```

Source: [https://github.com/DataOpsFusion/coactra/tree/main/examples/projects/support_desk](https://github.com/DataOpsFusion/coactra/tree/main/examples/projects/support_desk)
