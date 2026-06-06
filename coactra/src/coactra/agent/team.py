"""Lean Team registry — a bag of Agents + policy.

A Team groups Agents for capability routing (Workflow) and A2A who-may-talk
policy.  It is intentionally minimal: no hierarchy, no org-chart.

Public API
----------
- ``Team``  — roster + match + policy.
"""
from __future__ import annotations

from typing import Any, Callable

from coactra.agent.matcher import match_agent

__all__ = ["Team"]


def _default_policy(src: Any, dst: Any) -> bool:
    """Allow communication between agents that share the same tenant."""
    return getattr(src, "_tenant", None) == getattr(dst, "_tenant", None)


class Team:
    """A lean registry of Agent members with a capability matcher and talk policy.

    Parameters
    ----------
    members:
        List of Agent instances (or any objects exposing ``_name``, ``_tenant``,
        ``_skills``, and/or ``card``).
    match:
        Matching mode: ``"keyword"`` (default, deterministic token overlap) or
        ``"semantic"`` (cosine similarity via ``coactra.ai`` embeddings).
    policy:
        Callable ``(src_agent, dst_agent) -> bool`` determining whether *src*
        may call *dst*.  Defaults to same-tenant policy.
    """

    def __init__(
        self,
        members: list[Any],
        *,
        match: str = "keyword",
        policy: Callable[[Any, Any], bool] | None = None,
    ) -> None:
        self._members: list[Any] = list(members)
        self._mode: str = match
        self._policy: Callable[[Any, Any], bool] = policy if policy is not None else _default_policy

    # ------------------------------------------------------------------
    # Capability matching
    # ------------------------------------------------------------------

    def match(self, needs: str) -> Any | None:
        """Return the member whose skills best match *needs*, or ``None``.

        Delegates to :func:`match_agent` with the configured mode.
        """
        return match_agent(needs, self._members, mode=self._mode)

    # ------------------------------------------------------------------
    # Exact-name lookup
    # ------------------------------------------------------------------

    def member(self, name: str) -> Any | None:
        """Return the member with the given name, or ``None``."""
        for m in self._members:
            if getattr(m, "_name", None) == name:
                return m
        return None

    # ------------------------------------------------------------------
    # Talk policy
    # ------------------------------------------------------------------

    def can_talk(self, src: str, dst: str) -> bool:
        """Return True if the agent named *src* may communicate with *dst*.

        Uses the configured policy (default: same-tenant).  Returns ``False``
        when either name is not found in the roster.
        """
        src_agent = self.member(src)
        dst_agent = self.member(dst)
        if src_agent is None or dst_agent is None:
            return False
        return bool(self._policy(src_agent, dst_agent))

    # ------------------------------------------------------------------
    # Roster
    # ------------------------------------------------------------------

    def roster(self) -> list[dict]:
        """Return aggregated Agent Cards for all members that have skills.

        Cards are curated for discovery — they contain skills metadata only,
        no credentials, tokens, or raw tool names.
        """
        cards: list[dict] = []
        for m in self._members:
            card = getattr(m, "card", None)
            if isinstance(card, dict):
                cards.append(card)
        return cards
