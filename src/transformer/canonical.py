"""Canonical Profile Builder (doc 05, doc 06 M6).

Assembles the final CanonicalProfile. NEVER sees the config — this blindness
guarantees same-engine-no-code-changes. Immutable after build (doc 07 test).

PURE ASSEMBLER. It does not resolve conflicts, normalize, compute provenance,
compute confidence, or modify any field value — those are M3/M5. It only reads
the resolved values, attaches the already-computed confidences, and applies
PRESENTATION ORDERING (skills + provenance), then constructs the frozen profile.

overall_confidence: the Builder uses the Confidence Engine's mean verbatim
(0.74 on the sample). The gold fixture shows 0.79; investigation showed no
field-set/averaging policy reproduces 0.79 from the frozen per-field
confidences without changing the (frozen) confidence rules — e.g. it would need
2-source agreement scored 0.98 vs doc 04's table value 0.85, or dropping three
fields from the mean with no principled basis. Per instruction, the
mathematically-consistent value is preserved rather than reverse-fit.
"""
from __future__ import annotations

import re
from typing import Tuple

from .confidence import ConfidenceResult
from .conflict import ResolvedCandidate
from .models import CanonicalProfile, Location, ProvenanceEntry, Skill

# Provenance presentation order: identity/contact, the flagged employment
# conflict, skills (confidence-descending), then education — the order a
# reviewer reads a profile. Presentation only; entry CONTENT is fixed by M5.
_PROV_FIELD_RANK = {
    "full_name": 0, "emails": 1, "phones": 2, "location": 3,
    "links": 4, "headline": 5, "experience": 6, "skills": 7, "education": 8,
}


def _prov_rank(path: str) -> int:
    head = path.split(".", 1)[0].split("[", 1)[0]
    return _PROV_FIELD_RANK.get(head, 99)


def _candidate_id(full_name, emails) -> str:
    """Deterministic id from the name: lowercase, non-alphanumeric runs -> '-',
    trimmed, with a '-001' sequence suffix.  "Priya Sharma" -> "priya-sharma-001".

    The numeric suffix disambiguates same-named candidates; for a single resolved
    candidate it is always 001 (multi-candidate sequencing is the pipeline's job,
    M7). Falls back to the email local-part, then "candidate", if no name.
    """
    base = full_name or (emails[0].split("@")[0] if emails else "") or "candidate"
    slug = re.sub(r"[^a-z0-9]+", "-", base.lower()).strip("-") or "candidate"
    return f"{slug}-001"


def build(
    resolved: ResolvedCandidate,
    provenance: Tuple[ProvenanceEntry, ...],
    confidence: ConfidenceResult,
) -> CanonicalProfile:
    """Assemble one CanonicalProfile from the resolved values + provenance +
    confidence. Constructs the frozen profile once (immutable after build)."""
    per_field = confidence.per_field

    # skills: attach the already-computed confidence; sort confidence-descending,
    # ties broken by first-appearance (Python's sort is stable).
    skills = [
        Skill(name=s.name, confidence=per_field.get(f"skills.{s.name}"), sources=list(s.sources))
        for s in resolved.skills
    ]
    skills.sort(key=lambda sk: -(sk.confidence if sk.confidence is not None else 0.0))

    # provenance: same presentation ordering (field rank, skills by confidence).
    skill_conf = {f"skills.{s.name}": (per_field.get(f"skills.{s.name}") or 0.0) for s in resolved.skills}
    ordered_provenance = sorted(
        provenance,
        key=lambda p: (_prov_rank(p.field), -skill_conf.get(p.field, 0.0)),
    )

    return CanonicalProfile(
        candidate_id=_candidate_id(resolved.full_name, resolved.emails),
        full_name=resolved.full_name,
        emails=list(resolved.emails),
        phones=list(resolved.phones),
        location=resolved.location if resolved.location is not None else Location(),
        links=resolved.links,
        headline=resolved.headline,
        years_experience=None,  # not supplied by either source (gold: null)
        skills=skills,
        experience=list(resolved.experience),
        education=list(resolved.education),
        provenance=list(ordered_provenance),
        overall_confidence=confidence.overall,
    )
