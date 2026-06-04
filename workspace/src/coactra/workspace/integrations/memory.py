"""Journal distillation into a caller-provided memory facade."""

from __future__ import annotations

import json
from pathlib import Path

import structlog

log = structlog.get_logger("coactra.workspace.integrations.memory")

_DISTILL_PROMPT = """You are extracting durable facts from an agent's work journal.
Return a JSON array of short factual statements worth remembering long-term.
Include dates. Exclude transient chatter. If nothing is worth keeping, return [].

Journal entries:
{entries}
"""


def _already_distilled(journal_dir: Path) -> set[str]:
    marker = journal_dir / ".distilled"
    if not marker.exists():
        return set()
    return {line.strip() for line in marker.read_text().splitlines() if line.strip()}


def _mark_distilled(journal_dir: Path, filename: str) -> None:
    marker = journal_dir / ".distilled"
    with marker.open("a") as file:
        file.write(f"{filename}\n")


async def distill_journal(
    *,
    journal_dir: Path,
    agent_id: str,
    llm,
    memory,
    scope,
    acl=None,
) -> int:
    """Extract durable journal facts and write them through ``memory.remember``.

    ``memory`` and ``acl`` are duck typed so hosts can supply their own memory
    facade and authorization gate. The ACL is checked before any model call or
    write when supplied.
    """
    if not journal_dir.is_dir():
        return 0
    if acl is not None:
        acl.check_write(agent_id, scope)
    done = _already_distilled(journal_dir)
    total_facts = 0
    for entry in sorted(journal_dir.glob("*.md")):
        if entry.name in done:
            continue
        text = entry.read_text().strip()
        if not text:
            _mark_distilled(journal_dir, entry.name)
            continue
        response = await llm.ainvoke(_DISTILL_PROMPT.format(entries=text))
        raw = response.content if hasattr(response, "content") else str(response)
        try:
            facts = json.loads(raw)
        except json.JSONDecodeError:
            log.warning("distill_bad_json", agent=agent_id, file=entry.name)
            continue
        if not isinstance(facts, list):
            continue
        clean = [fact.strip() for fact in facts if isinstance(fact, str) and fact.strip()]
        if clean:
            await memory.remember(clean, scope=scope)
            total_facts += len(clean)
        _mark_distilled(journal_dir, entry.name)
    log.info("distill_complete", agent=agent_id, facts=total_facts)
    return total_facts
