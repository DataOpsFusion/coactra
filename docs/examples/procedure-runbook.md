# Procedure Runbook

Register a procedure, submit a work order that references it, and run it through
an `Orchestrator`.

```bash
python3 examples/work/procedure_runbook.py
```

The example uses a tiny in-process engine so the public contract is visible
without requiring LangGraph, Temporal, Prefect, or another workflow backend.

Source: [examples/work/procedure_runbook.py](https://github.com/DataOpsFusion/coactra/blob/main/examples/work/procedure_runbook.py)
