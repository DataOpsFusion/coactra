"""Structured skills and A2A Agent Card builder.

Pure data — no network, no pydantic-ai import.

Public API
----------
- ``Skill``             — frozen dataclass representing a curated skill entry.
- ``normalize_skills``  — accepts None / str / Skill / list[Skill|dict] → list[Skill].
- ``build_agent_card``  — produce an A2A-shaped Agent Card dict (curated, no creds).
"""
from __future__ import annotations

from dataclasses import dataclass, field

__all__ = ["Skill", "normalize_skills", "build_agent_card"]


# ---------------------------------------------------------------------------
# Skill dataclass
# ---------------------------------------------------------------------------

@dataclass(frozen=True)
class Skill:
    """A curated skill entry published on an A2A Agent Card.

    Parameters
    ----------
    id:
        Unique skill identifier (e.g. ``"cert.rotate"``).
    description:
        Human-readable summary of what the skill does.
    tags:
        Arbitrary labels for discovery/filtering.  Lists are accepted and
        normalised to tuples for hashability.
    scopes:
        OAuth 2.1 scopes required to invoke this skill.  Lists accepted and
        normalised to tuples.
    """

    id: str
    description: str = ""
    tags: tuple[str, ...] = field(default_factory=tuple)
    scopes: tuple[str, ...] = field(default_factory=tuple)

    def __post_init__(self) -> None:
        # Coerce mutable sequences → tuples so the frozen instance is truly
        # hashable even when the caller passes plain lists.
        object.__setattr__(self, "tags", tuple(self.tags))
        object.__setattr__(self, "scopes", tuple(self.scopes))


# ---------------------------------------------------------------------------
# normalize_skills
# ---------------------------------------------------------------------------

def normalize_skills(
    skills: None | str | Skill | list[Skill | dict],
) -> list[Skill]:
    """Normalise the ``skills=`` argument to a list of :class:`Skill` objects.

    Accepted forms
    --------------
    - ``None``             → ``[]``
    - ``str``              → ``[Skill(id="general", description=<str>)]``
    - :class:`Skill`       → ``[that skill]``
    - ``list``             → each item may be a :class:`Skill` or a ``dict``
                             with at least an ``"id"`` key; remaining keys
                             (``description``, ``tags``, ``scopes``) are
                             optional.
    """
    if skills is None:
        return []

    if isinstance(skills, str):
        return [Skill(id="general", description=skills)]

    if isinstance(skills, Skill):
        return [skills]

    # List path — items may be Skill instances or dicts
    result: list[Skill] = []
    for item in skills:
        if isinstance(item, Skill):
            result.append(item)
        elif isinstance(item, dict):
            result.append(
                Skill(
                    id=item["id"],
                    description=item.get("description", ""),
                    tags=item.get("tags", ()),
                    scopes=item.get("scopes", ()),
                )
            )
        else:
            raise TypeError(
                f"normalize_skills: expected Skill or dict, got {type(item)!r}"
            )
    return result


# ---------------------------------------------------------------------------
# build_agent_card
# ---------------------------------------------------------------------------

_DEFAULT_SECURITY_SCHEME: dict = {
    "bearerAuth": {
        "type": "http",
        "scheme": "bearer",
        "bearerFormat": "JWT",
    }
}


def build_agent_card(
    name: str,
    skills: None | str | Skill | list[Skill | dict],
    *,
    tenant: str | None = None,
    url: str | None = None,
    security_schemes: dict | None = None,
) -> dict:
    """Build an A2A-shaped Agent Card dict.

    The card is curated for public discovery — it contains **no** credentials,
    tokens, raw tool names, or argument schemas.  Only the curated skill
    metadata is included.

    Parameters
    ----------
    name:
        The agent's name (top-level ``"name"`` field).
    skills:
        Skill roster — passed through :func:`normalize_skills`.
    tenant:
        Optional tenant identifier.  Included if provided.
    url:
        Optional agent endpoint URL.
    security_schemes:
        OpenAPI-style ``securitySchemes`` dict.  Defaults to a simple bearer
        scheme if omitted.  Must not contain credentials.

    Returns
    -------
    dict
        A2A Agent Card with ``name``, optional ``url``, ``skills``,
        optional ``tenant``, and ``securitySchemes``.
    """
    normalised = normalize_skills(skills)

    skill_entries: list[dict] = []
    for sk in normalised:
        entry: dict = {
            "id": sk.id,
            "description": sk.description,
            "tags": list(sk.tags),
        }
        if sk.scopes:
            entry["scopes"] = list(sk.scopes)
        skill_entries.append(entry)

    card: dict = {"name": name}
    if url is not None:
        card["url"] = url
    if tenant is not None:
        card["tenant"] = tenant
    card["skills"] = skill_entries
    card["securitySchemes"] = (
        security_schemes if security_schemes is not None else _DEFAULT_SECURITY_SCHEME
    )
    return card
