"""Provenance Tracker (doc 04, doc 06 M5).

Per field: source, original, selected, rule, transforms. Captured AT resolution
time as a by-product of conflict.py. doc 05 Never Does: Modify canonical data.

Renders each FieldEvidence (produced by conflict.py) into the canonical
{field, source, method} ProvenanceEntry (doc 03 schema). doc 04's richer
provenance — selection rule, transforms, and the losing/conflicting value — is
encoded into the compound ``method`` string, exactly as the gold fixture does.
"""
from __future__ import annotations

from typing import Tuple

from .conflict import FieldEvidence, ResolvedCandidate
from .models import ProvenanceEntry


def _method(ev: FieldEvidence) -> str:
    """Render the compound method string for one resolved field."""
    if ev.category == "skills":
        # "union;agreement" | "union;single_source". (A ";notes_dispute" marker
        # would require a negative-skill signal the notes parser does not emit —
        # see the M5 note; the confidence value does not depend on it.)
        return ev.rule

    if ev.rule == "precedence" and ev.losing:
        chain = ">".join([ev.winner] + [s for s, _ in ev.losing])
        conflicts = ";".join(f"CONFLICT:{s}_asserts_{v}" for s, v in ev.losing)
        return f"precedence:{chain};{conflicts};flagged"

    if ev.rule == "agreement":
        method = "agreement:" + "+".join(ev.agreeing)
        if "E164" in ev.transforms:
            method += ";normalized:E164"
        return method

    return "single_source"


def build(resolved: ResolvedCandidate) -> Tuple[ProvenanceEntry, ...]:
    """One ProvenanceEntry per resolved field, in resolution order. The losing
    values live inside the method string — nothing is reconstructed later."""
    return tuple(
        ProvenanceEntry(field=ev.path, source=ev.winner, method=_method(ev))
        for ev in resolved.evidence
    )
