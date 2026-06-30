"""Person-name normalization (doc 04: Trim + collapse internal whitespace)."""
from __future__ import annotations

from typing import Optional


def normalize_name(raw: Optional[str]) -> Optional[str]:
    """Trim and collapse internal whitespace runs to single spaces.

    "  Priya   Sharma " -> "Priya Sharma"   ·   "" / non-str -> None

    Casing is preserved deliberately — personal names carry intentional casing
    (McArthur, de la Cruz) that title-casing would corrupt.
    """
    if not isinstance(raw, str):
        return None
    collapsed = " ".join(raw.split())
    return collapsed or None
