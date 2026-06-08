"""Candidate workflow drafting with a caller-provided language model."""

from __future__ import annotations

import re
from pathlib import Path

_PROPOSE_PROMPT = """Given this description of successful ad-hoc work, draft a
reusable procedure as YAML following our procedure schema (name, parameters,
nodes with id+type, edges). Use node types: tool, branch, human, python.
Do not invent tools you're unsure exist. Return only the YAML.

This is a CANDIDATE procedure for the procedure library. Once approved by the
operator it can be promoted through the host's procedure registration flow.

Work description:
{summary}
"""


def _safe_candidate_name(name: str) -> str:
    cleaned = re.sub(r"[^a-zA-Z0-9_-]+", "_", name.strip()).strip("_").lower()
    return cleaned or "candidate"


async def propose_candidate_workflow(
    *,
    work_order_summary: str,
    candidate_dir: Path,
    llm,
) -> Path:
    """Draft an inert candidate procedure file for later host-side approval."""
    candidate_dir.mkdir(parents=True, exist_ok=True)
    response = await llm.ainvoke(_PROPOSE_PROMPT.format(summary=work_order_summary))
    yaml_text = response.content if hasattr(response, "content") else str(response)
    name = "candidate"
    for line in yaml_text.splitlines():
        if line.strip().startswith("name:"):
            name = line.split(":", 1)[1].strip().strip("\"'")
            break
    target = candidate_dir / f"{_safe_candidate_name(name)}.yaml"
    target.write_text(
        "# CANDIDATE - proposed by an agent, NOT yet approved.\n"
        "# Review, then promote through the host procedure registration flow.\n"
        f"{yaml_text}",
        encoding="utf-8",
    )
    return target
