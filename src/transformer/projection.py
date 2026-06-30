"""Output Projection Engine — THE TWIST (doc 06 M6, doc 07 config-boundary test).

PURE: project(profile, config) -> dict. The ONLY code the config touches.
Selects fields, applies from remap, per-field normalize, toggles provenance/
confidence, applies on_missing in {null, omit, error}. MUST NOT mutate profile.

It reads a deep copy of the profile (dataclasses.asdict) and never touches the
frozen original, so the same CanonicalProfile can be projected through many
configs to produce many shapes with zero engine changes.
"""
from __future__ import annotations

import re
from dataclasses import asdict
from typing import Any, Dict, List, Tuple

from .models import CanonicalProfile, Config, OnMissing
from .normalize import normalize_phone, normalize_skill

_MISSING = object()  # sentinel: path did not resolve (distinct from a real None)

# per-field normalizers a config may request by name (doc 06 M6)
_NORMALIZERS = {"E164": normalize_phone, "canonical": normalize_skill}


class MissingFieldError(Exception):
    """Raised when on_missing='error' and a requested field is absent. The one
    intended hard failure (doc 05/08): contract-honoring, not a crash."""

    def __init__(self, path: str) -> None:
        self.path = path
        super().__init__(f"required field '{path}' is missing")


def _tokens(path: str) -> List[Tuple[str, Any]]:
    """Parse a path into walk tokens. Supports dotted keys, [i] indexing, and
    [] wildcard map: 'experience[0].company', 'emails[0]', 'skills[].name'."""
    toks: List[Tuple[str, Any]] = []
    for part in path.split("."):
        m = re.match(r"^([A-Za-z0-9_]*)(.*)$", part)
        name, rest = m.group(1), m.group(2)
        if name:
            toks.append(("key", name))
        for idx in re.findall(r"\[(\d*)\]", rest):
            toks.append(("wild", None) if idx == "" else ("index", int(idx)))
    return toks


def _resolve(data: Any, tokens: List[Tuple[str, Any]]) -> Any:
    """Walk tokens over a plain dict/list tree. Returns _MISSING if the path
    cannot be resolved (absent key / out-of-range index / descend into None)."""
    cur = data
    for i, (kind, val) in enumerate(tokens):
        if cur is _MISSING or cur is None:
            return _MISSING
        if kind == "key":
            if isinstance(cur, dict) and val in cur:
                cur = cur[val]
            else:
                return _MISSING
        elif kind == "index":
            if isinstance(cur, list) and -len(cur) <= val < len(cur):
                cur = cur[val]
            else:
                return _MISSING
        else:  # wildcard: map the remaining path over each list element
            if not isinstance(cur, list):
                return _MISSING
            rest = tokens[i + 1:]
            return [r for r in (_resolve(el, rest) for el in cur) if r is not _MISSING]
    return cur


def _apply_normalize(value: Any, name: str) -> Any:
    fn = _NORMALIZERS.get(name)
    if fn is None:
        return value  # unknown normalizer: passthrough (config is trusted, doc 08)
    if isinstance(value, list):
        return [fn(v) for v in value]
    return fn(value)


def _strip_confidence(obj: Any) -> None:
    """Recursively drop inline 'confidence' keys (when include_confidence=False)."""
    if isinstance(obj, dict):
        obj.pop("confidence", None)
        for v in obj.values():
            _strip_confidence(v)
    elif isinstance(obj, list):
        for v in obj:
            _strip_confidence(v)


def project(profile: CanonicalProfile, config: Config) -> Dict[str, Any]:
    """Project the canonical profile into the config's requested shape (pure)."""
    data = asdict(profile)  # deep copy — the frozen profile is never touched
    out: Dict[str, Any] = {}

    for spec in config.fields:
        value = _resolve(data, _tokens(spec.from_path or spec.path))
        if value is _MISSING:
            if config.on_missing is OnMissing.OMIT:
                continue
            if config.on_missing is OnMissing.ERROR:
                raise MissingFieldError(spec.path)
            value = None  # OnMissing.NULL
        if value is not None and spec.normalize:
            value = _apply_normalize(value, spec.normalize)
        out[spec.path] = value

    if config.include_provenance:
        out["provenance"] = data.get("provenance", [])
    if config.include_confidence:
        out["overall_confidence"] = data.get("overall_confidence")
    else:
        _strip_confidence(out)
    return out
