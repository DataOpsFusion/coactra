# Resolution Memory

Store prior support fixes and recall the most relevant resolution for a repeat
issue.

```bash
python3 examples/projects/resolution_memory/app.py
```

Shows:

- `Memory`
- `make_backend("inprocess")`
- scoped remember/recall calls

Production replacement: swap the backend to mem0 or Graphiti when you need
persistence or semantic recall.

Source: [examples/projects/resolution_memory](https://github.com/DataOpsFusion/coactra/tree/main/examples/projects/resolution_memory)
