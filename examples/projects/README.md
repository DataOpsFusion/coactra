# Sample Projects

Small runnable projects that show Coactra patterns without a class-heavy application design.

Install from the repository root:

```bash
python -m pip install -e "./coactra[all,dev]"
```

| Project | Shows | Run |
|---|---|---|
| `customer_support_memory` | support memory with `Memory.remember` and `Memory.recall` | `python3 examples/projects/customer_support_memory/app.py` |
| `support_desk` | agent draft + work lifecycle + ticket memory | `python3 examples/projects/support_desk/app.py` |
| `release_runner` | durable work lifecycle with `WorkManager` | `python3 examples/projects/release_runner/app.py` |
| `workspace_research_desk` | scoped workspace files, handoff, capability manifest | `python3 examples/projects/workspace_research_desk/app.py` |
| `multi_agent_policy` | policy-gated agent collaboration before A2A transport | `python3 examples/projects/multi_agent_policy/app.py` |

For focused work-order scripts (no project folder), see [../work/README.md](../work/README.md).

Examples use in-process defaults. Swap backend boundaries for production; keep application functions mostly unchanged.
