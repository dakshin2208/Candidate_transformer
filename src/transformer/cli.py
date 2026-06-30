"""Thin CLI — the ONLY surface (doc 06 M7, PDF lower-priority).

    python -m transformer --ats fixtures/ats.json \\
        --notes fixtures/recruiter-notes.txt \\
        --config configs/default-config.json

Wires the pipeline, prints JSON. No business logic. No REST/UI (descoped, doc 08).
Handles only file IO + arg parsing; the transformation lives in pipeline.py.
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import List, Optional, Tuple

from .models import Config
from .pipeline import transform
from .projection import MissingFieldError

_DEFAULT_CONFIG = "configs/default-config.json"


def main(argv: Optional[List[str]] = None) -> None:
    parser = argparse.ArgumentParser(
        prog="python -m transformer",
        description="Multi-Source Candidate Data Transformer",
    )
    parser.add_argument("--ats", help="path to ATS JSON file")
    parser.add_argument("--notes", help="path to recruiter notes .txt file")
    parser.add_argument("--github", help="path to GitHub JSON file (reserved for the stretch goal)")
    parser.add_argument("--config", default=_DEFAULT_CONFIG, help=f"path to config JSON (default: {_DEFAULT_CONFIG})")
    parser.add_argument("--output", help="optional path to write JSON result (default: stdout)")
    args = parser.parse_args(argv)

    # --- file IO (the only place files are read) ---
    sources: List[Tuple[str, str]] = []
    try:
        for source_id, path in (("ats", args.ats), ("notes", args.notes), ("github", args.github)):
            if path:
                sources.append((source_id, Path(path).read_text(encoding="utf-8")))
        config = Config.from_dict(json.loads(Path(args.config).read_text(encoding="utf-8")))
    except FileNotFoundError as exc:
        print(f"error: file not found: {exc.filename}", file=sys.stderr)
        sys.exit(1)

    # --- transform (on_missing='error' surfaces as MissingFieldError) ---
    try:
        outputs, failures = transform(sources, config)
    except MissingFieldError as exc:
        print(f"error: {exc}", file=sys.stderr)
        sys.exit(1)

    for failure in failures:
        print(f"[SKIP] {failure.source}: {failure.reason}", file=sys.stderr)

    # one candidate -> a single object (back-compat); otherwise a JSON array.
    result = outputs[0] if len(outputs) == 1 else outputs
    rendered = json.dumps(result, indent=2)
    if args.output:
        Path(args.output).write_text(rendered + "\n", encoding="utf-8")
        print(f"wrote {args.output}", file=sys.stderr)
    else:
        print(rendered)
    sys.exit(0)
