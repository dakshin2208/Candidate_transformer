"""Candidate Matching Engine (doc 04, doc 06 M4).

Exact-key priority: email>linkedin>github>phone>name+employer>name+location.
Phone alone never high-confidence when names disagree. NO fuzzy (descoped, doc 08).

Boundary (doc 05 "Never Does"): this module ONLY decides which records are the
same candidate and records the match strength. It does not merge, resolve
conflicts, score confidence, or build a profile. It depends on the Normalization
Engine purely to derive comparison keys (it never stores normalized values back —
records keep their raw values for M5 provenance).
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, FrozenSet, List, Optional, Sequence, Tuple

from .models import Location, SourceRecord
from .normalize import (
    normalize_company,
    normalize_country,
    normalize_email,
    normalize_name,
    normalize_phone,
)

# Canonical source ordering — the deterministic "stable source ordering" the
# final tiebreak refers to (doc 04). It replaces input-arrival "first-seen" so
# output is identical under shuffled input (doc 07 source-order independence).
# Reused by the Merge Engine now and the Conflict Resolution tiebreak in M5.
SOURCE_RANK = {"ats": 0, "resume": 1, "linkedin": 2, "github": 3, "notes": 4}


def source_sort_key(source: str) -> Tuple[int, str]:
    """Deterministic rank for a source id (unknown sources sort last, by name)."""
    return (SOURCE_RANK.get(source, 99), source)


_VERY_HIGH, _HIGH, _MEDIUM, _LOW = "very_high", "high", "medium", "low"


@dataclass(frozen=True)
class MatchResult:
    """How a cluster was matched — a *fact* about the match, NOT a confidence
    score (that is the Confidence Engine, M5). ``weak`` flags a priority 5-6
    match, which M5 turns into the documented -0.15 confidence penalty."""

    key: str        # email|linkedin|github|phone|name+employer|name+location|singleton
    priority: int   # 1-6; 0 for a singleton (no second record to match against)
    strength: str   # doc 04 "Match Confidence" label; "none" for a singleton
    weak: bool      # True iff matched on a low-priority key (5-6)


@dataclass(frozen=True)
class MatchedCluster:
    """One candidate's matched SourceRecords (canonical source order) + how they
    matched. Records are NOT merged here — that is the Merge Engine."""

    records: Tuple[SourceRecord, ...]
    match: MatchResult


@dataclass(frozen=True)
class _Keys:
    """Normalized comparison keys for one record (matching only; never stored
    back — the record keeps its raw values for M5 provenance)."""

    emails: FrozenSet[str]
    linkedin: Optional[str]
    github: Optional[str]
    phones: FrozenSet[str]
    name: Optional[str]
    employer: Optional[str]
    location: Optional[Tuple[str, str, str]]


def _canon_url(url: Optional[str]) -> Optional[str]:
    """Lightweight URL canonicalization for a matching key (scheme/www/trailing
    slash stripped, lowercased). Not a stored normalization — URLs are not one of
    doc 04's seven normalized field types; this only derives a comparison key."""
    if not isinstance(url, str) or not url.strip():
        return None
    u = url.strip().lower()
    for prefix in ("https://", "http://"):
        if u.startswith(prefix):
            u = u[len(prefix):]
            break
    if u.startswith("www."):
        u = u[4:]
    return u.rstrip("/") or None


def _location_key(loc: Location) -> Optional[Tuple[str, str, str]]:
    """A comparable (country, city, region) tuple, or None when location is empty."""
    country = normalize_country(loc.country) or (loc.country or "").strip().lower()
    city = (loc.city or "").strip().lower()
    region = (loc.region or "").strip().lower()
    if not (country or city or region):
        return None
    return (country, city, region)


def _keys(r: SourceRecord) -> _Keys:
    return _Keys(
        emails=frozenset(e for e in (normalize_email(x) for x in r.emails) if e),
        linkedin=_canon_url(r.links.linkedin),
        github=_canon_url(r.links.github),
        phones=frozenset(p for p in (normalize_phone(x) for x in r.phones) if p),
        name=normalize_name(r.full_name),
        employer=normalize_company(r.current_employer),
        location=_location_key(r.location),
    )


def _names_strongly_disagree(a: _Keys, b: _Keys) -> bool:
    """Both records name a person and the normalized names differ. Exact
    inequality only — fuzzy/similarity name matching is descoped (doc 08), so any
    difference counts. This is the SAFE direction for the phone safeguard: refuse
    a shared/recycled-number merge rather than guess."""
    return bool(a.name and b.name and a.name != b.name)


def _best_match(a: _Keys, b: _Keys) -> Optional[Tuple[int, str, str]]:
    """Highest-priority match key between two records, or None.
    Returns (priority, key_name, strength_label)."""
    if a.emails & b.emails:
        return (1, "email", _VERY_HIGH)
    if a.linkedin and a.linkedin == b.linkedin:
        return (2, "linkedin", _VERY_HIGH)
    if a.github and a.github == b.github:
        return (3, "github", _VERY_HIGH)
    if (a.phones & b.phones) and not _names_strongly_disagree(a, b):
        # SAFEGUARD: when names strongly disagree, phone alone does NOT match
        # (shared/office/recycled numbers); we fall through to weaker keys, which
        # require name equality and therefore also fail -> no merge.
        return (4, "phone", _HIGH)
    if a.name and a.name == b.name and a.employer and a.employer == b.employer:
        return (5, "name+employer", _MEDIUM)
    if a.name and a.name == b.name and a.location and a.location == b.location:
        return (6, "name+location", _LOW)
    return None


# --- union-find (deterministic: always reparent to the lower root index) -----
def _find(parent: List[int], i: int) -> int:
    while parent[i] != i:
        parent[i] = parent[parent[i]]
        i = parent[i]
    return i


def _union(parent: List[int], i: int, j: int) -> None:
    ri, rj = _find(parent, i), _find(parent, j)
    if ri != rj:
        parent[max(ri, rj)] = min(ri, rj)


def match(records: Sequence[SourceRecord]) -> List[MatchedCluster]:
    """Group records belonging to the same candidate (transitive over match
    edges) and record each cluster's strongest match key.

    Deterministic and order-independent: grouping is set-based, and both records
    within a cluster and the clusters themselves are sorted by canonical source
    rank — so shuffled input yields identical output (doc 07).
    """
    records = list(records)
    n = len(records)
    keys = [_keys(r) for r in records]

    parent = list(range(n))
    edges: List[Tuple[int, int, int, str, str]] = []
    for i in range(n):
        for j in range(i + 1, n):
            m = _best_match(keys[i], keys[j])
            if m is not None:
                edges.append((i, j, m[0], m[1], m[2]))
                _union(parent, i, j)

    members: Dict[int, List[int]] = {}
    for idx in range(n):
        members.setdefault(_find(parent, idx), []).append(idx)

    clusters: List[MatchedCluster] = []
    for root, idxs in members.items():
        internal = [e for e in edges if _find(parent, e[0]) == root]
        if internal:
            best = min(internal, key=lambda e: e[2])  # lowest priority number = strongest key
            result = MatchResult(key=best[3], priority=best[2], strength=best[4], weak=best[2] >= 5)
        else:
            result = MatchResult(key="singleton", priority=0, strength="none", weak=False)
        cluster_records = sorted((records[k] for k in idxs), key=lambda r: source_sort_key(r.source))
        clusters.append(MatchedCluster(records=tuple(cluster_records), match=result))

    clusters.sort(key=lambda c: source_sort_key(c.records[0].source))
    return clusters
