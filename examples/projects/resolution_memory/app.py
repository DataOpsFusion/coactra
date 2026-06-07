"""Resolution memory for repeat support issues.

Runs with the in-process memory backend. Replace the backend with mem0 or
Graphiti when you need persistence or semantic recall.
"""

from __future__ import annotations

from pprint import pprint

from coactra.memory import Memory, Scope, make_backend

SCOPE = Scope(tenant="acme", namespace="support", agent="helpdesk")


def build_memory() -> Memory:
    return Memory(backend=make_backend("inprocess"))


def record_resolution(memory: Memory, ticket_id: str, customer: str, fix: str) -> None:
    memory.sync.remember(
        [f"{ticket_id} customer={customer} fix={fix}"],
        scope=SCOPE,
    )


def suggest_fix(memory: Memory, issue: str) -> dict[str, object]:
    matches = memory.sync.recall(issue, scope=SCOPE, k=3)
    return {
        "issue": issue,
        "suggestion": matches[0].text if matches else "No prior fix found.",
        "evidence_count": len(matches),
    }


def main() -> None:
    memory = build_memory()
    record_resolution(memory, "T-100", "Globex", "rotate API key and restart worker")
    record_resolution(memory, "T-101", "Initech", "clear stale OAuth session")
    pprint(suggest_fix(memory, "API key worker failing"))


if __name__ == "__main__":
    main()
