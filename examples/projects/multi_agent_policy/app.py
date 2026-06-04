"""Multi-agent collaboration policy sample.

Shows where A2A belongs: behind a policy gate. The transport here is local and fake;
in production it would be `OfficialA2ATransport` from coactra.agent.adapters.
"""

from __future__ import annotations

from pprint import pprint

from coactra.agent import (
    AgentRef,
    AllowSameTenant,
    CollaborationDenied,
    PolicyGatedCollaborator,
    Scope,
)


class RecordingTransport:
    """Stateful transport boundary used only for the sample."""

    def __init__(self) -> None:
        self.sent: list[tuple[str, str]] = []

    def send(self, dst: AgentRef, question: str, scope: Scope) -> str:  # noqa: ARG002
        self.sent.append((dst.qualified_name, question))
        return f"reply from {dst.qualified_name}: check logs and recent deploys"


def ask_teammate(collaborator: PolicyGatedCollaborator, teammate: str | AgentRef, question: str) -> str:
    return collaborator.ask(teammate, question, {})


def run_policy_demo() -> dict[str, object]:
    scope = Scope(tenant_id="acme", namespace="agent:incident")
    transport = RecordingTransport()
    collaborator = PolicyGatedCollaborator(
        transport=transport,
        policy=AllowSameTenant(),
        scope=scope,
        me="agent:incident",
    )

    allowed = ask_teammate(collaborator, "agent:database", "Why is latency high?")

    try:
        ask_teammate(
            collaborator,
            AgentRef(tenant_id="globex", agent_id="agent:database"),
            "Can you inspect another tenant?",
        )
    except CollaborationDenied as exc:
        denied = str(exc)
    else:  # pragma: no cover - defensive; policy should deny before transport.
        denied = "unexpectedly allowed"

    return {
        "allowed_reply": allowed,
        "denied": denied,
        "wire_calls": transport.sent,
    }


def main() -> None:
    pprint(run_policy_demo())


if __name__ == "__main__":
    main()
