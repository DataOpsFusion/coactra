# Release Runner

A release pipeline as an authored Workflow: each stage is a `step`, human sign-offs are
approval pauses, and the whole run is durable.

## Code

```python
import asyncio
import os

from coactra import ModelProfile, ModelResolver, ModelRoute, Policy, Scope, StaticToken, Skill, Team, Workflow
from coactra.workflow import step


async def main(version: str) -> None:
    team = Team(
        scope=Scope(tenant_id="acme", namespace="release"),
        policy=Policy.permissive(),
        model_resolver=ModelResolver([
            ModelRoute(
                capability="release",
                profile=ModelProfile(
                    name="release",
                    model="openai/qwen3.6-plus",
                    api_base="https://opencode.ai/zen/go/v1",
                    api_key=os.environ["OC_KEY"],
                ),
            )
        ]),
    )
    await team.add_agent(
        model_capability="release",
        name="release-eng",
        auth=StaticToken("gateway-token"),
        gateway="https://gateway/mcp",
        skills=[Skill("release", description="Run release stages", tags=["pipeline", "execute"])],
        expose=True,
    )

    play = Workflow(f"release-{version}", steps=[
        step("run pre-release checks and tests", requires_skill="release", required_tags=["execute"]),
        step("build and push artifacts", requires_skill="release", required_tags=["execute"]),
        step("deploy to staging", requires_skill="release", required_tags=["execute"]),
        step("staging validation sign-off", approve=True, approval_only=True),
        step("deploy to production", requires_skill="release", required_tags=["execute"]),
        step("smoke-test production", requires_skill="release", required_tags=["execute"]),
        step("release manager sign-off", approve=True, approval_only=True),
        step("tag release and close", requires_skill="release", required_tags=["execute"]),
    ])

    run = await team.run(play)
    print(f"Release {version} -> {run.status}")
```
