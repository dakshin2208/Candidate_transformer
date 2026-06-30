"""Merge Engine (doc 04, doc 06 M4).

Combines matched records, PRESERVING every value. Never decides winners
(that is conflict.py). doc 05 Never Does: Decide which value wins.

Output shape: each candidate's evidence is regrouped from row-oriented
SourceRecords into a column-oriented per-field map of Contributions. Conflicting
values sit side by side (e.g. current_employer = [Stripe@ats, Databricks@notes]);
nothing is normalized, deduped, or selected. That is exactly the shape the
Conflict Resolution Engine (M5) consumes.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict, List, Sequence, Tuple

from .matcher import MatchResult, MatchedCluster
from .models import Links, Location

# Fields whose lists are flattened to one Contribution PER ITEM (each individual
# value preserved with the source that supplied it).
_LIST_FIELDS = ("emails", "phones", "skills", "experience", "education")
# Fields preserved as one Contribution PER SOURCE (scalar value or whole object).
_ATOMIC_FIELDS = ("full_name", "headline", "current_employer", "location", "links")


@dataclass(frozen=True)
class Contribution:
    """One source's value for one field — the atomic unit of preserved evidence.

    ``value`` is RAW (un-normalized): M5 normalizes the selected value and uses
    this original for provenance. For list fields it is a single item; for
    location/links it is the whole object.
    """

    source: str
    value: Any


@dataclass(frozen=True)
class MergedCandidate:
    """All evidence for one candidate, grouped per canonical field.

    Every value from every matched source is preserved and conflicting values are
    kept side by side. NO winner is chosen and NO value is normalized — both are
    M5's job.
    """

    sources: Tuple[str, ...]               # contributing sources, canonical order
    match: MatchResult                     # how the cluster matched (weak -> M5 penalty)
    fields: Dict[str, List[Contribution]]  # canonical field name -> all contributions


def _is_empty(value: Any) -> bool:
    """A value carries no evidence (so no Contribution is recorded)."""
    if value is None:
        return True
    if isinstance(value, str):
        return value.strip() == ""
    if isinstance(value, Location):
        return value.city is None and value.region is None and value.country is None
    if isinstance(value, Links):
        return (
            value.linkedin is None
            and value.github is None
            and value.portfolio is None
            and not value.other
        )
    return False


def merge_cluster(cluster: MatchedCluster) -> MergedCandidate:
    """Regroup one matched cluster's raw values into per-field evidence."""
    fields: Dict[str, List[Contribution]] = {}
    for record in cluster.records:  # already in canonical source order
        for fname in _LIST_FIELDS:
            for item in getattr(record, fname):
                if not _is_empty(item):
                    fields.setdefault(fname, []).append(Contribution(record.source, item))
        for fname in _ATOMIC_FIELDS:
            value = getattr(record, fname)
            if not _is_empty(value):
                fields.setdefault(fname, []).append(Contribution(record.source, value))
    return MergedCandidate(
        sources=tuple(r.source for r in cluster.records),
        match=cluster.match,
        fields=fields,
    )


def merge(clusters: Sequence[MatchedCluster]) -> List[MergedCandidate]:
    """Merge every matched cluster — one MergedCandidate per candidate."""
    return [merge_cluster(c) for c in clusters]
