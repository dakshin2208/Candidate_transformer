"""Shared data models — the canonical record and config.

Owns: the CanonicalProfile the engine always builds (doc 05 Canonical Profile
Builder) and the Config the projection layer consumes (doc 06 M1). The canonical
record is the single source of truth; the config NEVER mutates it.

Design notes (M1):
- Every canonical model is a *frozen* dataclass. The projection layer (doc 06
  M6 / doc 07 config-boundary test) must never mutate the canonical record, and
  ``frozen=True`` makes that a type-level guarantee. The engine assembles plain
  scratch data during M4/M5 and constructs these models once at the boundary
  ("immutable after build", canonical.py); any later edit uses
  ``dataclasses.replace`` to produce a new instance.
- Models are *pure data carriers*. Business invariants (confidence clamping,
  E.164/YYYY-MM normalization, winner selection) live in their owning engines
  per doc 05's "Never Does" boundaries — not here. The lone exception is Config,
  which is *external* input and gets minimal structural validation on load
  (doc 06 M1: "a config file loads and validates").
- Field names match doc 03's schema and the gold fixture exactly, so
  ``dataclasses.asdict(profile)`` serialises to the canonical JSON shape, in
  schema order, deterministically — no hand-written serialiser required.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Optional


class ConfigError(ValueError):
    """Raised when a config dict is structurally invalid (doc 06 M1).

    Subclasses ``ValueError`` so callers may catch either. This is a minimal
    in-module error; the broader *structured error model* (a separate M1
    deliverable) is deferred to keep this step to models.py as scoped.
    """


# ---------------------------------------------------------------------------
# Canonical record  (doc 03 schema · doc 04 field rules)
#
# Field names are exact. Normalized *forms* — E.164 phones, YYYY-MM dates,
# ISO-3166 alpha-2 country, canonical skill names — are produced by the
# Normalization Engine (M3) and merely *carried* here as strings. Unknown
# values are None, never fabricated (doc 04 Missing Data Policy).
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class Location:
    """location{city, region, country} (doc 03). ``country`` is ISO-3166 alpha-2."""

    city: Optional[str] = None
    region: Optional[str] = None
    country: Optional[str] = None


@dataclass(frozen=True)
class Links:
    """links{linkedin, github, portfolio, other[]} (doc 03)."""

    linkedin: Optional[str] = None
    github: Optional[str] = None
    portfolio: Optional[str] = None
    other: list[str] = field(default_factory=list)


@dataclass(frozen=True)
class Skill:
    """skills[{name, confidence, sources[]}] (doc 03 · doc 04 skills-union).

    ``sources`` lists every source that contributed this skill (union rule);
    ``confidence`` is scaled by source agreement by the Confidence Engine (M5)
    and is None until then.
    """

    name: str
    confidence: Optional[float] = None
    sources: list[str] = field(default_factory=list)


@dataclass(frozen=True)
class Experience:
    """experience[{company, title, start, end, summary}] (doc 03).

    ``start``/``end`` are YYYY-MM strings (doc 04); None when absent or
    unparseable (a current role has ``end=None``).
    """

    company: Optional[str] = None
    title: Optional[str] = None
    start: Optional[str] = None
    end: Optional[str] = None
    summary: Optional[str] = None


@dataclass(frozen=True)
class Education:
    """education[{institution, degree, field, end_year}] (doc 03)."""

    institution: Optional[str] = None
    degree: Optional[str] = None
    # Attribute named ``field`` to match the schema exactly. This class declares
    # no default_factory, so the module-level ``dataclasses.field`` is not
    # shadowed in a way that matters.
    field: Optional[str] = None
    end_year: Optional[int] = None


@dataclass(frozen=True)
class ProvenanceEntry:
    """provenance[{field, source, method}] (doc 03 · doc 04 Provenance Policy).

    doc 03's schema has exactly three keys. The gold fixture encodes doc 04's
    richer provenance — selection rule, transforms applied, and conflicting /
    losing values — inside the compound ``method`` string, e.g.::

        "agreement:ats+notes;normalized:E164"
        "precedence:ats>notes;CONFLICT:notes_asserts_Databricks;flagged"
        "union;single_source;notes_dispute"

    ``source`` records which source won (or "ats+notes" for an agreed/unioned
    field). All three keys are required — a provenance entry is always complete.
    """

    field: str
    source: str
    method: str


@dataclass(frozen=True)
class CanonicalProfile:
    """The single internal source of truth (doc 03 schema · doc 05 builder).

    ``candidate_id`` is the only required field — identity is mandatory. Every
    other field defaults to null/empty so a sparse or degraded profile always
    constructs without crashing (doc 01/02 graceful degradation). The engine
    always builds a *structurally complete* profile — every key present, every
    nested object an object not a bare null (doc 06 M6) — leaving the projection
    layer to decide the consumer-facing representation.
    """

    candidate_id: str
    full_name: Optional[str] = None
    emails: list[str] = field(default_factory=list)
    phones: list[str] = field(default_factory=list)
    location: Location = field(default_factory=Location)
    links: Links = field(default_factory=Links)
    headline: Optional[str] = None
    years_experience: Optional[int] = None
    skills: list[Skill] = field(default_factory=list)
    experience: list[Experience] = field(default_factory=list)
    education: list[Education] = field(default_factory=list)
    provenance: list[ProvenanceEntry] = field(default_factory=list)
    overall_confidence: Optional[float] = None


# ---------------------------------------------------------------------------
# Source-stage record  (doc 02 step 3 · doc 05 Source Parsers · M2)
#
# The common internal representation every parser emits: RAW extracted values
# from ONE source. No normalization, no merging (doc 05 Source Parsers "Never
# Does") — `source` tags provenance, M3 normalizes, M4 matches/merges, M5
# resolves. Every field is optional: a source is a partial view. ``experience``
# / ``education`` reuse the canonical shapes purely as containers, but hold raw
# (pre-normalization) values until M3 runs.
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class SourceRecord:
    """One source's raw contribution, keyed by ``source`` ("ats", "notes", ...)."""

    source: str
    full_name: Optional[str] = None
    emails: list[str] = field(default_factory=list)
    phones: list[str] = field(default_factory=list)
    location: Location = field(default_factory=Location)
    links: Links = field(default_factory=Links)
    headline: Optional[str] = None
    # "where they work now" — feeds match key 5 (name+employer) and the
    # employment-conflict resolution (doc 04); distinct from experience[] history.
    current_employer: Optional[str] = None
    skills: list[str] = field(default_factory=list)  # raw names; canonicalized in M3
    experience: list[Experience] = field(default_factory=list)
    education: list[Education] = field(default_factory=list)


# ---------------------------------------------------------------------------
# Runtime output config  (doc 02 step 11 · doc 03 "the twist" · doc 06 M6)
#
# Consumed ONLY by the projection layer; never touches the engine. Structural
# deserialization + minimal validation lives here with the model; deeper
# semantic checks (do `from` paths resolve against the schema?) and file IO are
# the Input Validator's job (validate.py, doc 05 / M2-M6).
# ---------------------------------------------------------------------------


class OnMissing(str, Enum):
    """on_missing ∈ {null, omit, error} (doc 03 · doc 06 M6).

    ``str`` mix-in so a member compares to / serialises as its plain JSON
    string. ``ERROR`` is the one intended hard failure (doc 05/08): a
    contract-honoring behavior the caller requested, not a crash.
    """

    NULL = "null"
    OMIT = "omit"
    ERROR = "error"


@dataclass(frozen=True)
class FieldSpec:
    """One entry in ``config.fields`` (doc 06 M6).

    ``path``      — output key in the projected shape.
    ``from_path`` — canonical path to read from (JSON key ``"from"``; renamed
                    because ``from`` is a reserved word). None ⇒ projection reads
                    ``path`` itself (that default is applied in M6, not stored).
    ``normalize`` — optional per-field normalizer name (e.g. "E164",
                    "canonical"). Kept an open string, not an enum, so new
                    normalizers plug in without a model change — unlike
                    ``on_missing``'s closed three-value set.
    """

    path: str
    from_path: Optional[str] = None
    normalize: Optional[str] = None

    @classmethod
    def from_dict(cls, d: dict) -> "FieldSpec":
        path = d.get("path")
        if not isinstance(path, str) or not path:
            raise ConfigError(f"each field needs a non-empty string 'path'; got {d!r}")
        return cls(path=path, from_path=d.get("from"), normalize=d.get("normalize"))


@dataclass(frozen=True)
class Config:
    """Runtime projection config (doc 03 twist · doc 06 M6).

    ``from_dict`` performs *structural* validation only (M1 done-criteria: "a
    config file loads and validates"). Semantic validation — that every
    ``from_path`` resolves against the canonical schema — belongs to the
    projection / output validator (M6).
    """

    fields: list[FieldSpec]
    include_provenance: bool = True
    include_confidence: bool = True
    on_missing: OnMissing = OnMissing.NULL
    description: Optional[str] = None

    @classmethod
    def from_dict(cls, d: dict) -> "Config":
        if not isinstance(d, dict):
            raise ConfigError("config must be a JSON object")
        raw_fields = d.get("fields")
        if not isinstance(raw_fields, list) or not raw_fields:
            raise ConfigError("config 'fields' must be a non-empty list")
        raw_on_missing = d.get("on_missing", OnMissing.NULL.value)
        try:
            on_missing = OnMissing(raw_on_missing)
        except ValueError:
            allowed = [m.value for m in OnMissing]
            raise ConfigError(
                f"on_missing must be one of {allowed}; got {raw_on_missing!r}"
            )
        return cls(
            fields=[FieldSpec.from_dict(f) for f in raw_fields],
            include_provenance=bool(d.get("include_provenance", True)),
            include_confidence=bool(d.get("include_confidence", True)),
            on_missing=on_missing,
            description=d.get("description"),
        )
