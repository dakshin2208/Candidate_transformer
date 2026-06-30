"""Confidence Engine (doc 04, doc 06 M5).

Rule-based, NOT ML. Consumes provenance. Base 0.98/0.85/0.70/0.40,
weak-match -0.15, clamp [0,1], ties -> lower. overall = mean of per-field.

Consumes the resolution evidence (the structured provenance facts conflict.py
produced — which sources contributed, which won) and the MatchResult (the weak
flag). It never changes a selected value (doc 05 Never Does).

Per-field source reliability is field-specific (doc 01): for SKILLS, ATS/LinkedIn
are low-reliability (keyword-style skill lists) while hands-on sources
(notes/github/resume) are reliable — which is why a single-ATS skill scores 0.40
and a single-notes skill scores 0.70. For all other fields every source is
treated as reliable.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, Optional

from .conflict import FieldEvidence, ResolvedCandidate

# Sources that are LOW-reliability for a given field category (doc 01).
_LOW_RELIABILITY = {
    "skills": {"ats", "linkedin"},
}

_WEAK_PENALTY = 0.15


@dataclass(frozen=True)
class ConfidenceResult:
    per_field: Dict[str, float]
    overall: Optional[float]


def _reliable(source: str, category: str) -> bool:
    return source not in _LOW_RELIABILITY.get(category, set())


def _clamp(x: float) -> float:
    return round(max(0.0, min(1.0, x)), 2)


def _field_confidence(ev: FieldEvidence) -> float:
    """Base score from agreement + reliability, then penalties (doc 04)."""
    if ev.category == "skills":
        # skills scale: 2+ contributing sources -> 0.98; else by reliability.
        if len(ev.agreeing) >= 2:
            base = 0.98
        else:
            base = 0.70 if _reliable(ev.agreeing[0], "skills") else 0.40
    else:
        # base table over the count of AGREEING reliable sources (doc 04).
        reliable = [s for s in ev.agreeing if _reliable(s, ev.category)]
        n = len(reliable)
        if n >= 3:
            base = 0.98
        elif n == 2:
            base = 0.85
        elif n == 1:
            base = 0.70
        elif ev.agreeing:  # only low-reliability source(s) supported the value
            base = 0.40
        else:
            base = 0.0

    if ev.weak:  # priority 5-6 match penalty, applied after the base score
        base -= _WEAK_PENALTY
    return _clamp(base)


def score(resolved: ResolvedCandidate) -> ConfidenceResult:
    """Per-field confidence for every resolved field + the overall mean.

    overall_confidence is the mean of the included per-field confidences
    (deterministic given the same fields).
    """
    per_field = {ev.path: _field_confidence(ev) for ev in resolved.evidence}
    overall = round(sum(per_field.values()) / len(per_field), 2) if per_field else None
    return ConfidenceResult(per_field=per_field, overall=overall)
