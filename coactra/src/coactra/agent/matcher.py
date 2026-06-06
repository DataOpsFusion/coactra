"""Capability matcher for Team — keyword (default) and semantic modes.

Pure-data helpers; no pydantic-ai / network imports at module level.

Public API
----------
- ``match_agent(needs, members, *, mode)`` — find the best-matching member
  by skill overlap (keyword) or cosine similarity (semantic).
- ``_get_embedder``                         — internal hook; monkeypatch in tests.
"""
from __future__ import annotations

import re
from typing import Any

__all__ = ["match_agent"]


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------

def _tokenize(text: str) -> set[str]:
    """Lowercase, split on whitespace and punctuation, return non-empty tokens."""
    return {t for t in re.split(r"[\s\W]+", text.lower()) if t}


def _skill_tokens(member: Any) -> set[str]:
    """Return all keyword tokens from a member's skills.

    Reads ``_skills`` (list of Skill) directly from the Agent's private attr;
    falls back to the public ``card`` property when ``_skills`` is absent
    (future-proofing for duck-typed members).
    """
    tokens: set[str] = set()

    skills = getattr(member, "_skills", None)
    if skills is not None:
        for sk in skills:
            tokens |= _tokenize(sk.id)
            tokens |= _tokenize(sk.description)
            for tag in sk.tags:
                tokens |= _tokenize(tag)
        return tokens

    # Fallback: read from Agent Card dict
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
        for sk in skills:
            parts.append(sk.id)
            if sk.description:
                parts.append(sk.description)
            parts.extend(sk.tags)
        return " ".join(parts)

    card = getattr(member, "card", None)
    if isinstance(card, dict):
        for entry in card.get("skills", []):
            parts.append(entry.get("id", ""))
            parts.append(entry.get("description", ""))
            parts.extend(entry.get("tags", []))
    return " ".join(p for p in parts if p)


def _get_embedder():
    """Return a callable(text) -> list[float].  Lazily imports coactra.ai.

    This function is a named hook so tests can monkeypatch it without touching
    the heavy import machinery.
    """
    try:
        from coactra.ai.completion.embedding import LiteLLMEmbedding
    except ImportError as exc:
        raise ImportError(
            "Semantic matching requires coactra[ai]; "
            "install with: pip install coactra[ai]"
        ) from exc
    return LiteLLMEmbedding()


# ---------------------------------------------------------------------------
# Keyword matcher
# ---------------------------------------------------------------------------

def _keyword_match(needs: str, members: list[Any]) -> Any | None:
    """Return the member with the highest token-overlap score vs *needs*.

    Ties → first member in list wins.  Zero overlap → None.
    """
    needs_tokens = _tokenize(needs)
    if not needs_tokens:
        return None

    best_member = None
    best_score = 0

    for member in members:
        # Trivial match: exact name
        name = getattr(member, "_name", None)
        if name is not None and name in needs:
            return member

        score = len(needs_tokens & _skill_tokens(member))
        if score > best_score:
            best_score = score
            best_member = member

    return best_member if best_score > 0 else None


# ---------------------------------------------------------------------------
# Semantic matcher
# ---------------------------------------------------------------------------

def _semantic_match(needs: str, members: list[Any]) -> Any | None:
    """Return the member whose skills text is nearest to *needs* by cosine sim.

    Raises ``ImportError`` if coactra[ai]/numpy is unavailable.
    """
    from coactra.ai.completion.embedding import cosine  # always available if [ai] installed

    embedder = _get_embedder()  # may raise ImportError → surfaces to caller
    needs_vec = embedder(needs)

    best_member = None
    best_sim = -1.0

    for member in members:
        text = _skill_text(member)
        if not text.strip():
            continue
        member_vec = embedder(text)
        sim = cosine(needs_vec, member_vec)
        if sim > best_sim:
            best_sim = sim
            best_member = member

    return best_member


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def match_agent(needs: str, members: list[Any], *, mode: str = "keyword") -> Any | None:
    """Return the member whose skills best match *needs*, or ``None``.

    Parameters
    ----------
    needs:
        Natural-language description of the capability needed (e.g.
        ``"rotate the cert"``).
    members:
        List of Agent instances (or any object with ``_name``, ``_skills``,
        and/or ``card``).
    mode:
        ``"keyword"`` (default) — token/substring overlap, deterministic,
        no model call.  ``"semantic"`` — cosine similarity via
        ``coactra.ai`` embeddings; raises ``ImportError`` if unavailable.

    Returns
    -------
    The best-matching member, or ``None`` when nothing matches.
    """
    if not members:
        return None

    if mode == "keyword":
        return _keyword_match(needs, members)
    elif mode == "semantic":
        return _semantic_match(needs, members)
    else:
        raise ValueError(f"Unknown match mode {mode!r}; expected 'keyword' or 'semantic'")
