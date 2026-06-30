"""Email normalization (doc 04: Trim whitespace, lowercase)."""
from __future__ import annotations

from typing import Optional


def normalize_email(raw: Optional[str]) -> Optional[str]:
    """Trim + lowercase. ``None`` for non-strings, blanks, or non-email-shaped
    values (no ``@``) — doc 04: unparseable -> None, never fabricate."""
    if not isinstance(raw, str):
        return None
    cleaned = raw.strip().lower()
    if not cleaned or "@" not in cleaned:
        return None
    return cleaned
