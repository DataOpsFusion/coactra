# Release Work Lifecycle

Focused scripts for durable work orders.

```bash
python3 examples/work/release_work_lifecycle.py
python3 examples/work/change_approval_gate.py
```

`release_work_lifecycle.py` shows submit, claim, start, checkpoint, complete, and
audit events.

`change_approval_gate.py` shows a work order pausing for human approval, receiving
a decision, being claimed again, and completing with an artifact.

Production replacement: use `SqlWorkStore` or another persistent `WorkStore` when
work state must survive process restarts.

Source: [examples/work](https://github.com/DataOpsFusion/coactra/tree/main/examples/work)
