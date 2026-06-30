"""Normalization Engine (doc 04 Normalization, doc 06 M3).

Pure functions, parser-independent (parallelizable per doc 06).
Unparseable -> None + provenance note. NEVER fabricate.
Functions: email, phone(E164), date(YYYY-MM), country(ISO-2), skill, name, company.
"""
from .company import normalize_company
from .country import normalize_country
from .date import normalize_date
from .email import normalize_email
from .name import normalize_name
from .phone import normalize_phone
from .skill import normalize_skill

__all__ = [
    "normalize_email",
    "normalize_phone",
    "normalize_date",
    "normalize_country",
    "normalize_skill",
    "normalize_name",
    "normalize_company",
]
