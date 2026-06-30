"""Recruiter Notes parser — UNSTRUCTURED source (doc 06 M2).

FREE-TEXT EXTRACTION: phone/email/employer/skills from prose via regex.
NO AI, fully deterministic (doc 07: tested against the fixed fixture).

Guiding rule (keeps this consistent with the gold profile, the source of
truth): extract the call's *substantive, explicitly-stated findings* — contact
details, the employer CHANGE, and the skills discussed. Do NOT re-assert
identity the note only mentions in passing (the header name, "Based in SF",
"Berkeley grad"): the ATS is authoritative for those, and the gold marks them
single_source. Matching back to the ATS record is carried by the email/phone
the recruiter explicitly recorded, so the header name is not needed as data.
"""
from __future__ import annotations

import re
from typing import ClassVar, Iterable, Optional

from ..models import SourceRecord
from .base import SourceParser

# -- Contact ------------------------------------------------------------------
# Standard email shape. First match wins; values stay raw (M3 lowercases).
_EMAIL_RE = re.compile(r"[A-Za-z0-9._%+\-]+@[A-Za-z0-9.\-]+\.[A-Za-z]{2,}")
# Phone: optional +country, then area(3) / exchange(3) / line(4), tolerant of
# spaces, dots, dashes and parens between groups. The full 3-3-4 structure is
# required, so stray numbers ("06/2026", "0142") never match. Raw -> E.164 (M3).
_PHONE_RE = re.compile(r"\+?\d{1,3}[\s.\-]?\(?\d{3}\)?[\s.\-]?\d{3}[\s.\-]?\d{4}")

# -- Current employer ---------------------------------------------------------
# Capture the Proper-Noun company AFTER an employment-CHANGE cue, so we get the
# employer she MOVED TO (Databricks). "her LinkedIn still says Stripe" carries
# no cue, so the stale employer is deliberately NOT captured.
_EMPLOYER_RE = re.compile(
    r"(?:moved to|now at|joined|currently at|works?\s+at)\s+"
    r"([A-Z][\w.&]*(?:\s+[A-Z][\w.&]*)*)"
)

# -- Skills -------------------------------------------------------------------
# Recognition vocabulary — spotting only; canonical de-aliasing is M3's job.
# Matched case-sensitively on word boundaries against this canonical casing,
# which keeps short/ambiguous tokens safe ("Go" the skill, not "go"/"ago").
_SKILL_VOCAB = (
    "Python", "Go", "Rust", "Java", "JavaScript", "TypeScript",
    "Kubernetes", "Docker", "PostgreSQL", "MySQL", "Redis", "Kafka",
    "React", "Node.js", "AWS", "GCP", "Terraform", "Ruby", "Scala",
)
# A mention is dropped when a negation cue sits just before it, so
# "Did NOT claim PostgreSQL depth ..." excludes PostgreSQL while the unqualified
# Python/Go/Kubernetes/Rust are kept.
_NEGATION_RE = re.compile(r"\b(?:not|never|no|n't)\b", re.IGNORECASE)
_NEGATION_WINDOW = 30  # chars before a mention to scan for a negation cue


class NotesParser(SourceParser):
    source_name: ClassVar[str] = "notes"

    def parse(self, raw: str) -> SourceRecord:
        text = raw or ""
        return SourceRecord(
            source=self.source_name,
            emails=_unique(_EMAIL_RE.findall(text)),
            phones=_unique(m.group(0).strip() for m in _PHONE_RE.finditer(text)),
            current_employer=self._employer(text),
            skills=self._skills(text),
        )

    @staticmethod
    def _employer(text: str) -> Optional[str]:
        match = _EMPLOYER_RE.search(text)
        return match.group(1) if match else None

    @staticmethod
    def _skills(text: str) -> list:
        found = []
        for skill in _SKILL_VOCAB:
            for m in re.finditer(rf"\b{re.escape(skill)}\b", text):
                before = text[max(0, m.start() - _NEGATION_WINDOW):m.start()]
                if _NEGATION_RE.search(before):
                    continue  # negated mention -> keep scanning for a clean one
                found.append((m.start(), skill))
                break  # first non-negated mention is enough
        # deterministic: order by first appearance in the text
        return [skill for _, skill in sorted(found)]


def _unique(items: Iterable[str]) -> list:
    """Order-preserving de-dup of truthy strings (deterministic output)."""
    seen, out = set(), []
    for item in items:
        if item and item not in seen:
            seen.add(item)
            out.append(item)
    return out
