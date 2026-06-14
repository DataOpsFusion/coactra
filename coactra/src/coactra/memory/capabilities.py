"""Capability — the ONE vocabulary used by BOTH export negotiation and recall shaping.

A backend declares the subset it supports. export() intersects source and target sets;
the difference is what gets dropped/degraded (and reported). recall() callers pass the
subset THEY can consume so results are shaped to what they understand.
"""

from __future__ import annotations

from enum import Enum, auto


class Capability(Enum):
    STORE = auto()  # can persist/retrieve items at all (baseline)
    LEXICAL_RECALL = auto()  # token/substring matching
    VECTOR_EMBEDDING = auto()  # semantic similarity via embeddings
    GRAPH_EDGES = auto()  # typed relationships between items
    MEMORY_BLOCK = auto()  # Letta-style self-edited blocks
    TEMPORAL = auto()  # bitemporal validity (Graphiti-style)
    PROVENANCE = auto()  # preserves item lineage
