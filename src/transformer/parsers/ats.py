"""ATS JSON parser — STRUCTURED source (doc 06 M2).

Exercises FIELD REMAPPING: ATS uses fullName/contactEmail/mobile/
currentEmployer/... which do NOT match canonical names.

The remap tables below ARE that requirement, expressed as data: the ATS's
foreign field names are translated to our canonical attribute names here, on
input, and never leak past this parser. Values stay RAW — casing, phone
punctuation, "United States" vs "US" are all left for the Normalization Engine
(M3); a parser that normalized would violate doc 05's "Never Does".
"""
from __future__ import annotations

import json
from typing import ClassVar

from ..models import Education, Experience, Links, Location, SourceRecord
from .base import SourceParser, SourceParseError

# ATS foreign name -> our canonical name. Each table targets one shape.
_SCALAR_REMAP = {           # -> SourceRecord scalar attributes
    "fullName": "full_name",
    "jobTitle": "headline",
    "currentEmployer": "current_employer",
}
_LOCATION_REMAP = {         # -> Location attributes
    "city": "city",
    "state": "region",
    "countryName": "country",
}
_EXPERIENCE_REMAP = {       # -> Experience attributes (per employmentHistory row)
    "employer": "company",
    "role": "title",
    "startDate": "start",
    "endDate": "end",
}
_EDUCATION_REMAP = {        # -> Education attributes (per educationHistory row)
    "school": "institution",
    "degreeName": "degree",
    "fieldOfStudy": "field",
    "graduationYear": "end_year",
}


def _remap(row: dict, table: dict) -> dict:
    """Apply one remap table to a dict row -> {canonical_attr: raw_value}.

    Missing source keys map to ``None`` (graceful — never a KeyError).
    """
    return {attr: row.get(ats_name) for ats_name, attr in table.items()}


class ATSParser(SourceParser):
    source_name: ClassVar[str] = "ats"

    def parse(self, raw: str) -> SourceRecord:
        try:
            payload = json.loads(raw)
        except (json.JSONDecodeError, TypeError) as exc:
            raise SourceParseError(self.source_name, f"invalid JSON: {exc}") from exc
        if not isinstance(payload, dict):
            raise SourceParseError(self.source_name, "top-level JSON is not an object")
        applicant = payload.get("applicant")
        if not isinstance(applicant, dict):
            raise SourceParseError(self.source_name, "missing 'applicant' object")

        scalars = _remap(applicant, _SCALAR_REMAP)

        # contactEmail / mobile remap into the canonical list-valued fields.
        emails = [applicant["contactEmail"]] if applicant.get("contactEmail") else []
        phones = [applicant["mobile"]] if applicant.get("mobile") else []
        skills = [s for s in (applicant.get("skillsList") or []) if isinstance(s, str)]

        # List sections: skip any malformed (non-dict) row rather than crash.
        experience = [
            Experience(**_remap(row, _EXPERIENCE_REMAP))
            for row in (applicant.get("employmentHistory") or [])
            if isinstance(row, dict)
        ]
        education = [
            Education(**_remap(row, _EDUCATION_REMAP))
            for row in (applicant.get("educationHistory") or [])
            if isinstance(row, dict)
        ]

        return SourceRecord(
            source=self.source_name,
            full_name=scalars["full_name"],
            emails=emails,
            phones=phones,
            location=Location(**_remap(applicant, _LOCATION_REMAP)),
            links=Links(linkedin=applicant.get("linkedinUrl")),
            headline=scalars["headline"],
            current_employer=scalars["current_employer"],
            skills=skills,
            experience=experience,
            education=education,
        )
