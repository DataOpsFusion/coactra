# Customer Support Memory

Use this when your app needs to remember prior tickets, customer preferences,
operational lessons, or conversation facts.

## Demonstrates

- `coactra.memory.Memory`
- `make_backend("inprocess")` for local development
- tenant-scoped `remember` and `recall`
- application logic as plain functions

## Run

```bash
python3 examples/projects/customer_support_memory/app.py
```

## Production Swap

```python
memory = Memory(backend=make_backend("graphiti", ...))
```

Source: [https://github.com/DataOpsFusion/coactra/tree/main/examples/projects/customer_support_memory](https://github.com/DataOpsFusion/coactra/tree/main/examples/projects/customer_support_memory)
