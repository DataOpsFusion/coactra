# Approval Routing

Policy-gated agent collaboration before any A2A transport sends work.

```bash
python3 examples/projects/approval_routing/app.py
```

The transport is local and fake. The important behavior is that same-tenant
collaboration is allowed and cross-tenant collaboration is denied before the
transport boundary.

Source: [examples/projects/approval_routing](https://github.com/DataOpsFusion/coactra/tree/main/examples/projects/approval_routing)
