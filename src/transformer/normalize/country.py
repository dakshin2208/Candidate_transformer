"""Country normalization to ISO-3166 alpha-2 (doc 04: US, IN).

A real alias lookup table (common hiring markets), not a stub. Already-alpha-2
input passes through (US -> US). Unknown -> None (doc 04: never fabricate). No
IO: the table is in-module so the function stays pure and deterministic.
"""
from __future__ import annotations

from typing import Optional

# ISO-3166 alpha-2 -> recognised name aliases (all matched case-insensitively).
_COUNTRIES = {
    "US": ("united states", "united states of america", "usa", "u.s.", "u.s.a.", "america"),
    "CA": ("canada",),
    "GB": ("united kingdom", "uk", "u.k.", "great britain", "britain", "england"),
    "IN": ("india", "bharat"),
    "DE": ("germany", "deutschland"),
    "FR": ("france",),
    "ES": ("spain", "espana", "españa"),
    "IT": ("italy", "italia"),
    "NL": ("netherlands", "holland"),
    "IE": ("ireland",),
    "PT": ("portugal",),
    "BE": ("belgium",),
    "CH": ("switzerland",),
    "AT": ("austria",),
    "SE": ("sweden",),
    "NO": ("norway",),
    "DK": ("denmark",),
    "FI": ("finland",),
    "PL": ("poland",),
    "UA": ("ukraine",),
    "RU": ("russia", "russian federation"),
    "AU": ("australia",),
    "NZ": ("new zealand",),
    "SG": ("singapore",),
    "JP": ("japan",),
    "CN": ("china", "prc", "people's republic of china"),
    "HK": ("hong kong",),
    "KR": ("south korea", "korea", "republic of korea"),
    "TW": ("taiwan",),
    "BR": ("brazil", "brasil"),
    "MX": ("mexico", "méxico"),
    "AR": ("argentina",),
    "CL": ("chile",),
    "CO": ("colombia",),
    "IL": ("israel",),
    "AE": ("united arab emirates", "uae"),
    "SA": ("saudi arabia",),
    "TR": ("turkey", "turkiye", "türkiye"),
    "ZA": ("south africa",),
    "NG": ("nigeria",),
    "KE": ("kenya",),
    "EG": ("egypt",),
    "PK": ("pakistan",),
    "BD": ("bangladesh",),
    "ID": ("indonesia",),
    "PH": ("philippines",),
    "VN": ("vietnam", "viet nam"),
    "TH": ("thailand",),
    "MY": ("malaysia",),
}

# Flatten to alias -> code, then add each alpha-2 code as a passthrough alias.
_ALIAS_TO_ISO2 = {alias: code for code, aliases in _COUNTRIES.items() for alias in aliases}
for _code in _COUNTRIES:
    _ALIAS_TO_ISO2[_code.lower()] = _code


def normalize_country(raw: Optional[str]) -> Optional[str]:
    """Map a country name/code to ISO-3166 alpha-2, else ``None``.

    "United States" -> "US"   ·   "India" -> "IN"   ·   "US" -> "US"
    unknown / garbage -> None   (never raises, never fabricates)
    """
    if not isinstance(raw, str):
        return None
    key = raw.strip().lower()
    if not key:
        return None
    return _ALIAS_TO_ISO2.get(key)
