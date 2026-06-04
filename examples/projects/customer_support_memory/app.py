"""Customer support memory sample.

Shows coactra-memory as a small remember/recall facade. No agent subclassing, no
external database, no API keys. Swap make_backend("inprocess") for mem0 or graphiti
when you want a real memory engine.
"""

from __future__ import annotations

from coactra.memory import Memory, Scope, make_backend


SUPPORT_SCOPE = Scope(tenant="acme", namespace="support", agent="helpdesk")


def build_memory() -> Memory:
    return Memory(backend=make_backend("inprocess"))


def learn_from_ticket(memory: Memory, ticket_id: str, customer: str, resolution: str) -> None:
    memory.sync.remember(
        [f"ticket {ticket_id}: customer={customer}; resolution={resolution}"],
        scope=SUPPORT_SCOPE,
    )


def answer_repeat_issue(memory: Memory, issue: str) -> dict[str, object]:
    hits = memory.sync.recall(issue, scope=SUPPORT_SCOPE, k=3)
    if not hits:
        return {"answer": "No prior resolution found.", "evidence": []}
    return {
        "answer": f"Use the prior fix: {hits[0].text}",
        "evidence": [hit.model_dump(mode="json") for hit in hits],
    }


def main() -> None:
    memory = build_memory()
    learn_from_ticket(memory, "T-100", "Globex", "rotate API key and restart worker")
    learn_from_ticket(memory, "T-101", "Initech", "clear stale OAuth session")

    result = answer_repeat_issue(memory, "API key worker")
    print(result)


if __name__ == "__main__":
    main()
