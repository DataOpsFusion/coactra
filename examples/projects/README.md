# Sample Projects

These are small runnable projects that show different ways to use Coactra without forcing a class-heavy application design.

| Project | Shows | Run |
|---|---|---|
| `customer_support_memory` | support memory with `Memory.remember` and `Memory.recall` | `PYTHONPATH=memory/src python3 examples/projects/customer_support_memory/app.py` |
| `release_runner` | durable work lifecycle with `WorkManager` | `PYTHONPATH=orchestration/src python3 examples/projects/release_runner/app.py` |
| `workspace_research_desk` | scoped workspace files, handoff, and capability manifest | `PYTHONPATH=workspace/src python3 examples/projects/workspace_research_desk/app.py` |
| `multi_agent_policy` | policy-gated agent collaboration before A2A transport | `PYTHONPATH=agent/src python3 examples/projects/multi_agent_policy/app.py` |

The examples intentionally use in-process or local defaults. Replace the backend boundary when moving to production; keep the application functions mostly unchanged.
