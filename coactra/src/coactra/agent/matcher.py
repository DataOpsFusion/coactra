"""Fuzzy member ranking helpers for future skill-query adapters.

The Team-first alpha path routes workflow steps by exact ``requires_skill`` ids
through ``Team.match_skill()``. This module remains as an internal helper for
future fuzzy or semantic skill-query adapters; it is not part of the preferred
public execution path.
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


def _skill_text(member: Any) -> str:
    """Return a single text string of all skill content for embedding."""
    parts: list[str] = []

    skills = getattr(member, "_skills", None)
    if skills is not None:
        for skill in skills:
            parts.append(skill.id)
            if skill.description:
                parts.append(skill.description)
            parts.extend(skill.tags)
        return " ".join(parts)

    card = getattr(member, "card", None)
    if isinstance(card, dict):
        for entry in card.get("skills", []):
            parts.append(entry.get("id", ""))
            parts.append(entry.get("description", ""))
            parts.extend(entry.get("tags", []))
    return " ".join(part for part in parts if part)


def _get_embedder():
    """Return a callable(text) -> list[float]."""
    try:
        from coactra.ai.completion.embedding import LiteLLMEmbedding
    except ImportError as exc:
        raise ImportError(
            "Semantic matching requires coactra[ai]; install with: pip install coactra[ai]"
        ) from exc
    return LiteLLMEmbedding()


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


def _semantic_match(query: str, members: list[Any], *, embedder: Any = None) -> Any | None:
    """Return the member whose skills text is nearest to *query* by cosine similarity."""
    from coactra.ai.completion.embedding import cosine

    embedder = embedder or _get_embedder()
    query_vec = embedder(query)

    best_member = None
    best_sim = -1.0

    for member in members:
        text = _skill_text(member)
        if not text.strip():
            continue
        member_vec = embedder(text)
        sim = cosine(query_vec, member_vec)
        if sim > best_sim:
            best_sim = sim
            best_member = member

    return best_member


def match_agent(
    query: str,
    members: list[Any],
    *,
    mode: str = "keyword",
    embedder: Any = None,
) -> Any | None:
    """Return the member whose effective skills best match *query*, or ``None``."""
    if not members:
        return None

    if mode == "keyword":
        return _keyword_match(query, members)
    if mode == "semantic":
        return _semantic_match(query, members, embedder=embedder)
    raise ValueError(f"Unknown match mode {mode!r}; expected 'keyword' or 'semantic'")
