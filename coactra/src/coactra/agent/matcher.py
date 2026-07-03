"""Keyword member ranking helpers.

The Team-first alpha path routes workflow steps by exact ``requires_skill`` ids
through ``Team.match_skill()``. This module remains as a tiny internal keyword
fallback; it is not part of the preferred public execution path.
"""

from __future__ import annotations

import re
from typing import Any

__all__ = ["match_agent"]


def _tokenize(text: str) -> set[str]:
    """Lowercase, split on whitespace and punctuation, return non-empty tokens."""
    return {token for token in re.split(r"[\s\W]+", text.lower()) if token}


def _skill_tokens(member: Any) -> set[str]:
    """Return keyword tokens from a member's effective skills."""
    tokens: set[str] = set()

    skills = getattr(member, "_skills", None)
    if skills is not None:
        for skill in skills:
            tokens |= _tokenize(skill.id)
            tokens |= _tokenize(skill.description)
            for tag in skill.tags:
                tokens |= _tokenize(tag)
        return tokens

    card = getattr(member, "card", None)
    if isinstance(card, dict):
        for entry in card.get("skills", []):
            tokens |= _tokenize(entry.get("id", ""))
            tokens |= _tokenize(entry.get("description", ""))
            for tag in entry.get("tags", []):
                tokens |= _tokenize(tag)
    return tokens


def _keyword_match(query: str, members: list[Any]) -> Any | None:
    """Return the member with the highest token-overlap score vs *query*."""
    query_tokens = _tokenize(query)
    if not query_tokens:
        return None

    best_member = None
    best_score = 0

    for member in members:
        name = getattr(member, "_name", None)
        if isinstance(name, str) and name in query:
            return member

        score = len(query_tokens & _skill_tokens(member))
        if score > best_score:
            best_score = score
            best_member = member

    return best_member if best_score > 0 else None


def match_agent(
    query: str,
    members: list[Any],
    *,
    mode: str = "keyword",
) -> Any | None:
    """Return the member whose effective skills best match *query*, or ``None``."""
    if not members:
        return None

    if mode == "keyword":
        return _keyword_match(query, members)
    raise ValueError(f"Unknown match mode {mode!r}; expected 'keyword'")
