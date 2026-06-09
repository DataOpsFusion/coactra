"""Approval-routed agent collaboration.

The transport is local and fake. The point is the boundary: cross-agent calls go
through shared Policy before any A2A transport is allowed to send work.
"""

from __future__ import annotations

import asyncio
from pprint import pprint

from coactra import Decision, DecisionOutcome, PolicyRequest
from coactra.agent import AgentRef, AsyncPolicyGatedCollaborator, CollaborationDenied, Scope


class TenantOnlyPolicy:
    async def check(self, request: PolicyRequest) -> Decision:
        if request.context.get("src_tenant") != request.context.get("dst_tenant"):
            return Decision(outcome=DecisionOutcome.deny, reason="cross-tenant denied")
        return Decision(outcome=DecisionOutcome.allow, source="demo")


class RecordingTransport:
    def __init__(self) -> None:
        self.sent: list[tuple[str, str]] = []

    async def send(self, dst: AgentRef, question: str, scope: Scope) -> str:  # noqa: ARG002
        self.sent.append((dst.qualified_name, question))
        return f"reply from {dst.qualified_name}: inspect deploys, queues, and database load"


async def run_routing_demo() -> dict[str, object]:
    scope = Scope(tenant_id="acme", namespace="ops", agent_id="oncall")
    transport = RecordingTransport()
    collaborator = AsyncPolicyGatedCollaborator(
        transport=transport,
        policy=TenantOnlyPolicy(),
        scope=scope,
        me="oncall",
    )

    allowed = await collaborator.ask("database", "Why did checkout latency spike?", {})

    try:
        await collaborator.ask(
            AgentRef(tenant_id="globex", agent_id="database"),
            "Can you inspect another tenant?",
            {},
        )
    except CollaborationDenied as exc:
        denied = str(exc)
    else:
        denied = "unexpectedly allowed"

    return {
        "allowed_reply": allowed,
        "denied": denied,
        "transport_calls": transport.sent,
    }


def main() -> None:
    pprint(asyncio.run(run_routing_demo()))


if __name__ == "__main__":
    main()
