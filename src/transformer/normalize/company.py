"""Company-name normalization (doc 04: Trim + normalize casing, e.g. Google).

Casing is normalized CONSERVATIVELY: uniformly-cased input (ALL CAPS or all
lowercase) is title-cased, but mixed-case input is preserved. This fixes the
"GOOGLE"/"google" -> "Google" case from doc 04 while protecting intentional
brand casing (eBay, LinkedIn, Databricks, PostgreSQL) that naive title-casing
would corrupt — the classic title-case-breaks-brands bug. Acronym-only names
("ibm") are a known limitation of best-effort casing; an acronym dictionary is
the extension point.
"""
from __future__ import annotations

from typing import Optional


def normalize_company(raw: Optional[str]) -> Optional[str]:
    """Trim, collapse whitespace, normalize obviously-uniform casing.

    "  Stripe " -> "Stripe"   ·   "GOOGLE" -> "Google"   ·   "eBay" -> "eBay"
    "" / non-str -> None
    """
    if not isinstance(raw, str):
        return None
    collapsed = " ".join(raw.split())
    if not collapsed:
        return None
    if collapsed.isupper() or collapsed.islower():
        return collapsed.title()
    return collapsed
