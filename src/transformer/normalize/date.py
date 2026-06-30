"""Date normalization to YYYY-MM (doc 04: Coerce to YYYY-MM, e.g. 2023-07).

Year-only input ("2019") -> None. CHOICE (documented): we do NOT fabricate a
month. doc 04 forbids inventing missing data, and "2019" -> "2019-01" would
manufacture a January that the source never stated. Honestly-empty beats
wrong-but-confident. (A standalone graduation year lives in education.end_year
as an int, never routed through this function.)
"""
from __future__ import annotations

import re
from typing import Optional

# YYYY then MM, with -, / or . separators; an optional day is accepted + dropped.
_YYYY_MM = re.compile(r"^(\d{4})[-/.](\d{1,2})(?:[-/.]\d{1,2})?$")
_YEAR_ONLY = re.compile(r"^\d{4}$")


def normalize_date(raw: Optional[str]) -> Optional[str]:
    """Coerce to ``YYYY-MM``, else ``None``.

    "2022-03" -> "2022-03"   (passthrough)
    "2022/3"  -> "2022-03"   (zero-padded, separators normalized)
    "2019"    -> None        (year-only: month not fabricated)
    garbage   -> None        (never raises)
    """
    if not isinstance(raw, str):
        return None
    s = raw.strip()
    if not s:
        return None

    m = _YYYY_MM.match(s)
    if m:
        year, month = m.group(1), int(m.group(2))
        if 1 <= month <= 12:
            return f"{year}-{month:02d}"
        return None  # impossible month -> unparseable

    if _YEAR_ONLY.match(s):
        return None  # documented: no month -> None, never fabricated

    return None
