# Extensions

Use extensions when an external system should add capabilities to Coactra
without becoming a Coactra subsystem.

Good extension candidates:

| External system | Extension should install |
|---|---|
| Pi or Hermes agent packages | skills, model routes, runtime adapters, or A2A peers |
| Claude Code or Codex integrations | A2A peer configs, MCP servers, policy rules, work ledgers |
| Internal platform package | tenant policy, auth, workspace, memory, and approved tools |

The extension owns its SDK details. Coactra only gives it a scoped Team to
register against:

```python
from dataclasses import dataclass

from coactra import Skill, Team, TeamExtension


@dataclass
class HermesExtension:
    name: str = "hermes"

    async def install(self, team: Team) -> None:
        team.add_skill(
            Skill(
                "code.review",
                description="Review code changes through the host Hermes system",
                tags=["review", "code"],
            )
        )
        # The real package may also call team.add_agent(...), register a
        # RemotePeer(...), add model routes, or attach MCP servers.
```

```python
await team.install_extension(HermesExtension())
```

Do not hide a complete coding agent behind a generic command wrapper unless the
host explicitly wants that behavior. For coding agents, prefer explicit
extension-owned policy, sandbox, approval, A2A, and MCP configuration.
