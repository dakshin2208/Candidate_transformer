"""Conflict Resolution Engine (doc 04, doc 06 M5).

Field-specific precedence: contact=ATS>resume>linkedin; employment=ATS>resume>
linkedin; skills=UNION+normalize+dedupe; education=resume>linkedin.
Global: null-skip fall-through; deterministic final tiebreak (priority, first-seen).

Receives a MergedCandidate and SELECTS the canonical value per field. It applies
the frozen Normalization Engine to the chosen value (recording the transform,
e.g. "E164") but NEVER deletes evidence: every losing/disagreeing value is
preserved on the FieldEvidence so the Provenance Tracker can explain it and the
Confidence Engine can score it. It does NOT compute confidence or build the
profile (doc 05 boundaries).
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict, List, Optional, Sequence, Tuple

from .matcher import MatchResult, source_sort_key
from .merge import Contribution, MergedCandidate
from .models import Education, Experience, Links, Location
from .normalize import (
    normalize_company,
    normalize_country,
    normalize_date,
    normalize_email,
    normalize_name,
    normalize_phone,
    normalize_skill,
)

# Field-specific precedence (doc 04). "Verified" contact == ATS-confirmed (doc 04/08).
# notes (and any source absent from a list) is handled by the final tiebreak:
# fall through to canonical SOURCE_RANK order among the actual contributors.
_PRECEDENCE = {
    "contact": ("ats", "resume", "linkedin"),
    "employment": ("ats", "resume", "linkedin"),
    "education": ("resume", "linkedin"),
    # personal / other / skills: no precedence list -> agreement then SOURCE_RANK
}


@dataclass(frozen=True)
class FieldEvidence:
    """Why a field has the value it has — the resolution facts the Provenance
    Tracker renders and the Confidence Engine scores. Losing/disagreeing values
    are preserved here; nothing is discarded."""

    path: str                                  # "full_name", "emails[0]", "experience[0].company", "skills.Python", ...
    winner: str                                # attributed source ("ats"), or joined for skills ("ats+notes")
    agreeing: Tuple[str, ...]                  # sources sharing the selected value
    losing: Tuple[Tuple[str, Any], ...]        # (source, raw_value) that disagreed — PRESERVED
    rule: str                                  # single_source | agreement | precedence | union
    transforms: Tuple[str, ...]                # normalization steps applied (e.g. ("E164",))
    category: str                              # contact|employment|education|personal|skills|other (reliability)
    weak: bool                                 # carried from MatchResult


@dataclass(frozen=True)
class ResolvedSkill:
    name: str
    sources: Tuple[str, ...]


@dataclass(frozen=True)
class ResolvedCandidate:
    """Canonical values selected from the merged evidence, plus the per-field
    evidence trail. M6's builder assembles these into a CanonicalProfile; M5's
    provenance/confidence read the evidence."""

    full_name: Optional[str]
    emails: Tuple[str, ...]
    phones: Tuple[str, ...]
    location: Optional[Location]
    links: Links
    headline: Optional[str]
    skills: Tuple[ResolvedSkill, ...]
    experience: Tuple[Experience, ...]
    education: Tuple[Education, ...]
    evidence: Tuple[FieldEvidence, ...]
    match: MatchResult


# --- selection helpers ------------------------------------------------------
def _select(normed: List[Tuple[str, Any]], precedence: Tuple[str, ...]) -> Tuple[Any, str]:
    """Pick (value, winning_source) from non-null (source, value) pairs.

    Precedence first (null-skip down the list); if no listed source contributed,
    fall to highest agreement, ties broken by canonical SOURCE_RANK (doc 04).
    """
    if precedence:
        for src in precedence:
            for s, v in normed:
                if s == src:
                    return v, s
    by_value: Dict[Any, List[str]] = {}
    for s, v in normed:
        by_value.setdefault(v, []).append(s)

    def value_key(item: Tuple[Any, List[str]]):
        value, sources = item
        best_supporter = min(sources, key=source_sort_key)
        return (-len(sources), source_sort_key(best_supporter))

    value, sources = min(by_value.items(), key=value_key)
    return value, min(sources, key=source_sort_key)


def _rule(agreeing: Tuple[str, ...], losing: Tuple[Tuple[str, Any], ...], used_precedence: bool) -> str:
    if losing:
        return "precedence"
    if len(agreeing) >= 2:
        return "agreement"
    return "single_source"


def _resolve_scalar(
    contribs: Sequence[Contribution],
    normalizer,
    category: str,
    path: str,
    weak: bool,
    transforms: Tuple[str, ...] = (),
) -> Tuple[Optional[Any], Optional[FieldEvidence]]:
    """Resolve one scalar field; return (value, evidence) or (None, None)."""
    normed = [(c.source, normalizer(c.value)) for c in contribs]
    normed = [(s, v) for s, v in normed if v is not None]  # null-skip
    if not normed:
        return None, None
    precedence = _PRECEDENCE.get(category, ())
    value, winner = _select(normed, precedence)
    agreeing = tuple(sorted({s for s, v in normed if v == value}, key=source_sort_key))
    losing = tuple((s, v) for s, v in normed if v != value)
    used_prec = bool(precedence) and any(s in precedence for s, _ in normed)
    evidence = FieldEvidence(
        path=path,
        winner=winner,
        agreeing=agreeing,
        losing=losing,
        rule=_rule(agreeing, losing, used_prec),
        transforms=transforms,
        category=category,
        weak=weak,
    )
    return value, evidence


def _resolve_skills(contribs: Sequence[Contribution], weak: bool) -> Tuple[Tuple[ResolvedSkill, ...], Tuple[FieldEvidence, ...]]:
    """Union skills across sources: normalize, dedupe by canonical name, keep the
    contributing sources on each (doc 04 skills policy). Nothing is dropped."""
    canon: Dict[str, List[str]] = {}
    order: List[str] = []
    for c in contribs:
        name = normalize_skill(c.value)
        if name is None:
            continue
        if name not in canon:
            canon[name] = []
            order.append(name)
        if c.source not in canon[name]:
            canon[name].append(c.source)

    skills: List[ResolvedSkill] = []
    evidence: List[FieldEvidence] = []
    for name in order:
        sources = tuple(sorted(canon[name], key=source_sort_key))
        skills.append(ResolvedSkill(name=name, sources=sources))
        evidence.append(
            FieldEvidence(
                path=f"skills.{name}",
                winner="+".join(sources),
                agreeing=sources,
                losing=(),
                rule="union;agreement" if len(sources) >= 2 else "union;single_source",
                transforms=("canonical",),
                category="skills",
                weak=weak,
            )
        )
    return tuple(skills), tuple(evidence)


def _resolve_experience(
    merged: MergedCandidate, weak: bool
) -> Tuple[Tuple[Experience, ...], List[FieldEvidence]]:
    """Select the experience list by employment precedence (ATS>resume>linkedin),
    normalizing each entry's dates/company. Reconcile the current employer with
    any other source's current_employer claim, preserving the loser as a conflict
    on experience[0].company (e.g. notes asserts Databricks vs ATS Stripe)."""
    exp_contribs = merged.fields.get("experience", [])
    if not exp_contribs:
        return (), []

    # winning source for the experience list (employment precedence, then SOURCE_RANK)
    sources_present = [c.source for c in exp_contribs]
    winner = next(
        (s for s in _PRECEDENCE["employment"] if s in sources_present),
        min(sources_present, key=source_sort_key),
    )
    raw_entries = [c.value for c in exp_contribs if c.source == winner]
    entries = tuple(
        Experience(
            company=normalize_company(e.company),
            title=e.title,
            start=normalize_date(e.start),
            end=normalize_date(e.end),
            summary=e.summary,
        )
        for e in raw_entries
    )

    evidence: List[FieldEvidence] = []
    if entries:
        current_company = entries[0].company
        # other sources' current_employer claims that disagree with the winner
        losing = tuple(
            (c.source, c.value)
            for c in merged.fields.get("current_employer", [])
            if c.source != winner and normalize_company(c.value) != current_company
        )
        evidence.append(
            FieldEvidence(
                path="experience[0].company",
                winner=winner,
                agreeing=(winner,),
                losing=losing,
                rule="precedence" if losing else "single_source",
                transforms=(),
                category="employment",
                weak=weak,
            )
        )
    return entries, evidence


def _resolve_education(contribs: Sequence[Contribution], weak: bool) -> Tuple[Tuple[Education, ...], List[FieldEvidence]]:
    """Select education by precedence (resume>linkedin, else SOURCE_RANK)."""
    if not contribs:
        return (), []
    sources_present = [c.source for c in contribs]
    winner = next(
        (s for s in _PRECEDENCE["education"] if s in sources_present),
        min(sources_present, key=source_sort_key),
    )
    entries = tuple(c.value for c in contribs if c.source == winner)
    evidence = [
        FieldEvidence(
            path="education[0]",
            winner=winner,
            agreeing=(winner,),
            losing=(),
            rule="single_source",
            transforms=(),
            category="education",
            weak=weak,
        )
    ] if entries else []
    return entries, evidence


def _resolve_list_scalars(
    contribs: Sequence[Contribution], normalizer, category: str, base_path: str, weak: bool
) -> Tuple[Tuple[Any, ...], List[FieldEvidence]]:
    """Resolve a list-valued contact field (emails/phones): normalize, dedupe
    (order-preserving), record agreement per surviving value at <base>[i]."""
    by_value: Dict[Any, List[str]] = {}
    order: List[Any] = []
    for c in contribs:
        v = normalizer(c.value)
        if v is None:
            continue
        if v not in by_value:
            by_value[v] = []
            order.append(v)
        if c.source not in by_value[v]:
            by_value[v].append(c.source)

    values: List[Any] = []
    evidence: List[FieldEvidence] = []
    precedence = _PRECEDENCE.get(category, ())
    transforms = ("E164",) if normalizer is normalize_phone else ()
    for i, v in enumerate(order):
        supporters = by_value[v]
        winner = next((s for s in precedence if s in supporters), min(supporters, key=source_sort_key))
        agreeing = tuple(sorted(supporters, key=source_sort_key))
        values.append(v)
        evidence.append(
            FieldEvidence(
                path=f"{base_path}[{i}]",
                winner=winner,
                agreeing=agreeing,
                losing=(),
                rule="agreement" if len(agreeing) >= 2 else "single_source",
                transforms=transforms,
                category=category,
                weak=weak,
            )
        )
    return tuple(values), evidence


def resolve(merged: MergedCandidate) -> ResolvedCandidate:
    """Resolve every field of one merged candidate into canonical values + a
    full evidence trail (no evidence deleted)."""
    weak = merged.match.weak
    f = merged.fields
    evidence: List[FieldEvidence] = []

    full_name, ev = _resolve_scalar(f.get("full_name", []), normalize_name, "personal", "full_name", weak)
    if ev:
        evidence.append(ev)

    emails, ev_emails = _resolve_list_scalars(f.get("emails", []), normalize_email, "contact", "emails", weak)
    evidence.extend(ev_emails)
    phones, ev_phones = _resolve_list_scalars(f.get("phones", []), normalize_phone, "contact", "phones", weak)
    evidence.extend(ev_phones)

    location, ev = _resolve_scalar(f.get("location", []), _norm_location, "personal", "location", weak)
    if ev:
        evidence.append(ev)
    linkedin, ev = _resolve_scalar(
        [Contribution(c.source, c.value.linkedin) for c in f.get("links", []) if c.value.linkedin],
        lambda u: u, "other", "links.linkedin", weak,
    )
    if ev:
        evidence.append(ev)
    links = Links(linkedin=linkedin)

    headline, ev = _resolve_scalar(f.get("headline", []), lambda s: (s or None), "other", "headline", weak)
    if ev:
        evidence.append(ev)

    skills, ev_skills = _resolve_skills(f.get("skills", []), weak)
    evidence.extend(ev_skills)

    experience, ev_exp = _resolve_experience(merged, weak)
    evidence.extend(ev_exp)
    education, ev_edu = _resolve_education(f.get("education", []), weak)
    evidence.extend(ev_edu)

    return ResolvedCandidate(
        full_name=full_name,
        emails=emails,
        phones=phones,
        location=location,
        links=links,
        headline=headline,
        skills=skills,
        experience=experience,
        education=education,
        evidence=tuple(evidence),
        match=merged.match,
    )


def _norm_location(loc: Location) -> Optional[Location]:
    """Normalize a Location's country to ISO-2 (city/region pass through)."""
    if loc is None:
        return None
    normalized = Location(
        city=loc.city,
        region=loc.region,
        country=normalize_country(loc.country) or loc.country,
    )
    if normalized.city is None and normalized.region is None and normalized.country is None:
        return None
    return normalized
