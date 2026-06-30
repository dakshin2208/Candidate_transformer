"""Pipeline orchestration (doc 06 M7). Thin wiring layer ONLY.

Calls the frozen components in order and passes each stage's output to the next
UNCHANGED. It contains no business logic: it does not normalize, filter,
reorder, repair, or transform any intermediate data. It reads counts solely to
log progress.

    parse_sources -> match -> merge -> resolve -> build_provenance
    -> score_confidence -> build_canonical -> project -> validate_output -> return

Produces ONE projected profile per matched candidate (doc 01: "one canonical
profile per candidate") — every cluster in `merged` is processed, never just the
first. Returns a list of outputs; the CLI renders a single object when there is
exactly one candidate and an array when there are several.
"""
from __future__ import annotations

import sys
from typing import Dict, List, Tuple

from . import canonical, confidence, conflict, provenance
from .matcher import match
from .merge import merge
from .models import Config
from .parsers import default_parsers
from .projection import project
from .validate import SourceFailure, parse_sources, validate_output


def _log(prefix: str, message: str) -> None:
    print(f"[{prefix}] {message}", file=sys.stderr)


def transform(
    sources: List[Tuple[str, str]], config: Config
) -> Tuple[List[Dict], List[SourceFailure]]:
    """Run the full transformation and return (projected_outputs, failures).

    projected_outputs has one dict per matched candidate. failures lists sources
    that were skipped (reported, never raised). If ALL sources fail to parse,
    returns ([], failures). A MissingFieldError from projection
    (on_missing='error') propagates — it is an intentional, contract-honoring
    hard failure, not a crash.
    """
    parsed = parse_sources(sources, default_parsers())
    _log("PARSE", f"{len(parsed.records)} records, {len(parsed.failures)} failures")
    if not parsed.records:
        return [], list(parsed.failures)

    clusters = match(parsed.records)
    _log("MATCH", f"{len(clusters)} candidate cluster(s)")

    merged = merge(clusters)
    _log("MERGE", f"{len(merged)} merged candidate(s)")

    # One canonical profile PER candidate — process every cluster, never drop
    # evidence (doc 01: "one canonical profile per candidate").
    outputs: List[Dict] = []
    for candidate in merged:
        resolved = conflict.resolve(candidate)
        _log("RESOLVE", f"{len(resolved.evidence)} fields resolved")

        prov = provenance.build(resolved)
        conf = confidence.score(resolved)
        profile = canonical.build(resolved, prov, conf)
        _log(
            "BUILD",
            f"{profile.candidate_id}: {len(profile.provenance)} provenance entries, "
            f"overall_confidence={profile.overall_confidence}",
        )

        output = project(profile, config)
        errors = validate_output(output, config)
        _log("PROJECT", f"{len(output)} keys; " + ("valid" if not errors else f"{len(errors)} error(s): {errors}"))
        outputs.append(output)

    return outputs, list(parsed.failures)
