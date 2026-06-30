"""Input + Output Validation (doc 05, doc 06 M2/M6).

Input: malformed source -> skip + report, never crash.
Output: validate projected dict against requested schema before return.

M2 builds the input half. ``parse_sources`` is the input layer's "report and
continue" loop (doc 05 Input Validator failure handling): it validates each
source, delegates parsing to injected parsers, and converts every failure into
a structured SourceFailure so a single bad source can never abort the run. The
output half (schema validation) arrives with the projection layer in M6.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, Iterable, List, Mapping, Optional, Sequence, Tuple

from .models import Config, OnMissing, SourceRecord
from .parsers.base import SourceParseError, SourceParser

#: one source to process: (source id, already-read content). File IO is the
#: caller's job (the CLI, M7); the input layer works on content in memory.
SourceInput = Tuple[str, str]


@dataclass(frozen=True)
class SourceFailure:
    """A source that was skipped, with the reason. "Reported" is structured data
    the caller can surface; a logging utility arrives with the CLI (M7)."""

    source: str
    reason: str


@dataclass(frozen=True)
class ParseResult:
    """Input-layer output: the records that parsed, plus the sources skipped.
    The run is whatever ``records`` holds; ``failures`` never aborts it."""

    records: Sequence[SourceRecord]
    failures: Sequence[SourceFailure]


def validate_source(
    source: str, content: Optional[str], parsers: Mapping[str, SourceParser]
) -> Optional[SourceFailure]:
    """Pure pre-parse checks: recognised source type + non-empty payload.

    Returns a SourceFailure to skip, or ``None`` to proceed. Does NOT parse or
    transform (doc 05 Input Validator "Never Does").
    """
    if source not in parsers:
        return SourceFailure(source, "unknown source type")
    if content is None or not content.strip():
        return SourceFailure(source, "empty source")
    return None


def parse_sources(
    inputs: Iterable[SourceInput], parsers: Mapping[str, SourceParser]
) -> ParseResult:
    """Run the input layer over (source, content) pairs.

    For each: validate, then parse inside a guard that funnels every error into
    a SourceFailure. One malformed/empty source is reported and skipped; the
    valid sources still produce records (doc 04 Error Handling; M2 done-when).
    """
    records: list = []
    failures: list = []
    for source, content in inputs:
        failure = validate_source(source, content, parsers)
        if failure is not None:
            failures.append(failure)
            continue
        try:
            records.append(parsers[source].parse(content))
        except SourceParseError as exc:
            failures.append(SourceFailure(source, exc.reason))
        except Exception as exc:  # defensive: an unexpected parser bug must not crash the run
            failures.append(SourceFailure(source, f"unexpected error: {exc}"))
    return ParseResult(records=records, failures=failures)


# --- Output half (M6): validate a projected dict against its config ---------
def validate_output(output: Dict, config: Config) -> List[str]:
    """Check a projected output against the requested schema. Returns a list of
    error strings (empty == valid). Does not raise (on_missing='error' is the
    projection's job, doc 05; this is the post-projection schema check).

    Checks: every requested field is present unless on_missing='omit' allows its
    absence; and the provenance/confidence toggles produced their keys.
    """
    errors: List[str] = []
    for spec in config.fields:
        if spec.path not in output and config.on_missing in (OnMissing.NULL, OnMissing.ERROR):
            errors.append(f"required field '{spec.path}' is missing from output")
    if config.include_provenance and "provenance" not in output:
        errors.append("include_provenance is set but 'provenance' is absent")
    if config.include_confidence and "overall_confidence" not in output:
        errors.append("include_confidence is set but 'overall_confidence' is absent")
    return errors
