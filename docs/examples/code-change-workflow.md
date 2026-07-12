# Code Change Workflow

`code_change(...)` is an optional recipe for the common
**implement -> verify* -> review -> optional human approval** pattern.

It does not replace dynamic workflow induction. It gives you one reusable, typed bootstrap
shape for code and operations changes while keeping routing, policy, and approval evidence in
the normal Workflow model.

## Demonstrates

- `coactra.agent.recipes.code_change(...)`
- multiple verifier roles with required vs advisory checks
- broad skill routing plus `required_tags`
- structured verification and review contracts
- policy-driven optional human approval

## Code

```python
import asyncio
import os

from coactra import ModelProfile, ModelResolver, ModelRoute, Policy, Scope, Skill, Team, Workflow
from coactra.agent.recipes import (
    CodeChangeRiskTier,
    VerificationCheck,
    VerifierRequirement,
    VerifierRole,
    code_change,
)


async def main() -> None:
    team = Team(
        scope=Scope(tenant_id="acme", namespace="web"),
        policy=Policy.permissive(),
        model_resolver=ModelResolver([
            ModelRoute(
                capability="python",
                profile=ModelProfile(name="python", model="openai/deepseek-v4-pro", api_base="https://opencode.ai/zen/go/v1", api_key=os.environ["OC_KEY"]),
            ),
            ModelRoute(
                capability="security",
                profile=ModelProfile(name="security", model="openai/deepseek-v4-pro", api_base="https://opencode.ai/zen/go/v1", api_key=os.environ["OC_KEY"]),
            ),
        ]),
    )

    await team.add_agent(
        model_capability="python",
        name="python-implementer",
        auth="dev-token",
        skills=[Skill("python", description="Implement Python changes", tags=["backend", "implement"])],
        expose=True,
    )
    await team.add_agent(
        model_capability="python",
        name="python-verifier",
        auth="dev-token",
        skills=[Skill("python", description="Verify Python changes", tags=["backend", "verify"])],
        expose=True,
    )
    await team.add_agent(
        model_capability="security",
        name="security-reviewer",
        auth="dev-token",
        skills=[Skill("security", description="Review risky changes", tags=["review", "web"])],
        expose=True,
    )

    plan = code_change(
        "checkout-hardening",
        implement_instruction="Patch the checkout service to reject invalid coupon signatures.",
        implement_skill="python",
        implement_tags=["implement"],
        verifier_roles=[
            VerifierRole(
                role="functional",
                skill="python",
                required_tags=["verify"],
                requirement=VerifierRequirement.required,
                checks=[
                    VerificationCheck(
                        id="pytest",
                        kind="command",
                        instruction="Run the checkout unit tests.",
                        params={"command": "pytest tests/checkout -q"},
                    ),
                    VerificationCheck(
                        id="health",
                        kind="http",
                        instruction="Confirm the staging health endpoint returns 200.",
                        params={"url": "https://staging.example/healthz", "method": "GET"},
                        success={"status_code": 200},
                    ),
                ],
            ),
            VerifierRole(
                role="security",
                skill="security",
                required_tags=["review"],
                requirement=VerifierRequirement.advisory,
                checks=[
                    VerificationCheck(
                        id="abuse-review",
                        kind="manual",
                        instruction="Assess abuse paths introduced by the coupon validation change.",
                    )
                ],
            ),
        ],
        review_skill="security",
        review_tags=["review"],
        risk_tier=CodeChangeRiskTier.high,
        human_approval="auto",
    )

    run = await team.run(plan.workflow)
    print(run.status)


asyncio.run(main())
```

## Notes

- The helper returns a `CodeChangeWorkflowPlan`, so execute `plan.workflow` like any other Workflow.
- The helper types live in `coactra.agent.recipes`; they are separate from the core `Workflow` runner.
- High- and medium-risk plans add a final `approval_only=True` human gate by default when `human_approval="auto"`.
