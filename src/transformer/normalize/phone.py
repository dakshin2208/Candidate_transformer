"""Phone normalization to E.164 (doc 04: Parse to E.164, e.g. +14155550123).

Approach: MANUAL digit-extraction + country-code logic (no `phonenumbers`).
The project is deliberately dependency-free and determinism is its core
property (doc 07 byte-stability) — a hardcoded normalizer has no library
metadata-version drift. Scope is the sample data's region (NANP / +1); a bare
10-digit number is assumed to be NANP. Full international parsing (national
trunk-prefix handling, per-region validation) is a documented extension point
where libphonenumber would slot in behind this same signature.
"""
from __future__ import annotations

import re
from typing import Optional

# NANP / US — the default region assumed for a bare national number (doc 08).
_DEFAULT_COUNTRY_CODE = "1"


def normalize_phone(raw: Optional[str]) -> Optional[str]:
    """Coerce a raw phone string to E.164 (``+<digits>``), else ``None``.

    "(415) 555-0142"   -> "+14155550142"   (bare NANP national, +1 assumed)
    "+1 415-555-0142"  -> "+14155550142"   (already international)
    garbage / too short / ambiguous -> None   (never raises, never fabricates)
    """
    if not isinstance(raw, str) or not raw.strip():
        return None
    has_plus = raw.lstrip().startswith("+")
    digits = re.sub(r"\D", "", raw)
    if not digits:
        return None

    if has_plus:
        # Already international: trust the caller-supplied country code.
        e164_digits = digits
    elif len(digits) == 10:
        # Bare national number -> assume the default region (NANP +1).
        e164_digits = _DEFAULT_COUNTRY_CODE + digits
    elif len(digits) == 11 and digits.startswith(_DEFAULT_COUNTRY_CODE):
        # NANP national with country/trunk prefix but no '+'.
        e164_digits = digits
    else:
        # No '+' and not NANP-shaped: country code is unknown -> honestly empty.
        return None

    # E.164: leading '+', total length 8..15 digits, no leading zero.
    if not (8 <= len(e164_digits) <= 15) or e164_digits.startswith("0"):
        return None
    return "+" + e164_digits
