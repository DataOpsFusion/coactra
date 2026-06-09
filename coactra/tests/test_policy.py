from __future__ import annotations

import asyncio

from coactra import Decision, DecisionOutcome, Policy, PolicyRequest, Scope


def test_root_policy_surface_is_available():
    assert Policy is not None
    assert Decision is not None
    assert DecisionOutcome.allow == "allow"


def test_decision_allowed_matches_outcome():
    assert Decision(outcome=DecisionOutcome.allow).allowed is True
    assert Decision(outcome=DecisionOutcome.deny).allowed is False
    assert Decision(outcome=DecisionOutcome.requires_approval).allowed is False


def test_policy_request_carries_scope():
    scope = Scope(tenant_id="acme", namespace="support", agent_id="triage", session_id="s-1")
    request = PolicyRequest(
        principal="agent:triage",
        action="memory.read",
        resource="memory:customer-profile",
        scope=scope,
        component="memory",
    )
    assert request.scope == scope
    assert request.component == "memory"


def test_permissive_policy_allows():
    decision = asyncio.run(
        Policy.permissive().check(
            PolicyRequest(
                principal="agent:triage",
                action="tool.call",
                resource="tool:search",
                scope=Scope(tenant_id="acme"),
                component="agent",
            )
        )
    )
    assert decision.outcome is DecisionOutcome.allow


def test_default_deny_policy_denies():
    decision = asyncio.run(
        Policy.default_deny().check(
            PolicyRequest(
                principal="agent:triage",
                action="tool.call",
                resource="tool:search",
                scope=Scope(tenant_id="acme"),
                component="agent",
            )
        )
    )
    assert decision.outcome is DecisionOutcome.deny


def test_observed_policy_records_checks():
    observed = Policy.observed(default=DecisionOutcome.allow)
    decision = asyncio.run(
        observed.check(
            PolicyRequest(
                principal="agent:triage",
                action="tool.call",
                resource="tool:search",
                scope=Scope(tenant_id="acme"),
                component="agent",
            )
        )
    )
    assert decision.outcome is DecisionOutcome.allow
    assert len(observed.decisions) == 1
    assert observed.decisions[0].action == "tool.call"


def test_from_authorizer_wraps_bool_style_check():
    class BoolAuthorizer:
        async def allowed(self, actor: str, access: str, scope) -> bool:
            return actor == "agent:allowed" and access == "read"

    policy = Policy.from_authorizer(
        BoolAuthorizer(),
        access_resolver=lambda request: request.context["access"],
    )

    allowed = asyncio.run(
        policy.check(
            PolicyRequest(
                principal="agent:allowed",
                action="memory.read",
                resource="memory:customer-profile",
                scope=Scope(tenant_id="acme"),
                component="memory",
                context={"access": "read"},
            )
        )
    )
    denied = asyncio.run(
        policy.check(
            PolicyRequest(
                principal="agent:blocked",
                action="memory.read",
                resource="memory:customer-profile",
                scope=Scope(tenant_id="acme"),
                component="memory",
                context={"access": "read"},
            )
        )
    )

    assert allowed.outcome is DecisionOutcome.allow
    assert denied.outcome is DecisionOutcome.deny


def test_policy_is_runtime_checkable_protocol():
    class AllowAll:
        async def check(self, request: PolicyRequest) -> Decision:
            return Decision(outcome=DecisionOutcome.allow)

    assert isinstance(AllowAll(), Policy)
