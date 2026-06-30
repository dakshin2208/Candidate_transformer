"""SourceParser interface (doc 05, doc 06 M2).

The pluggability boundary: every source implements parse() -> SourceRecord.
New sources (GitHub, CSV, Resume) plug in here with NO engine change.
"""
from __future__ import annotations

from abc import ABC, abstractmethod
from typing import ClassVar

from ..models import SourceRecord


class SourceParseError(Exception):
    """A source payload is structurally unparseable — corrupt JSON, wrong
    top-level shape, etc. NOT raised for missing/empty *fields*, which degrade
    to ``None`` (doc 04: never fabricate, never crash).

    The input layer (validate.py) catches this, records a SourceFailure, and
    keeps going: one bad source never crashes the run (doc 04 Error Handling).
    Carries ``source`` + ``reason`` so the skip can be reported as structured
    data. This is the first concrete error type — built now because M2's real
    failures (bad JSON) define it, not speculatively.
    """

    def __init__(self, source: str, reason: str) -> None:
        self.source = source
        self.reason = reason
        super().__init__(f"[{source}] {reason}")


class SourceParser(ABC):
    """Contract for every source parser.

    ``parse`` extracts a SourceRecord of RAW values and MUST NOT normalize or
    merge (doc 05 Source Parsers "Never Does"). It raises SourceParseError on
    structurally unparseable input; a missing field becomes ``None``, never a
    crash. Parsers take already-read content (a ``str``), not a path, so they
    are unit-testable in isolation (doc 07) and file IO stays at the boundary.
    """

    #: stable source id, used for provenance and the parser registry ("ats", ...)
    source_name: ClassVar[str] = ""

    @abstractmethod
    def parse(self, raw: str) -> SourceRecord:
        """Raw source content -> SourceRecord. Raise SourceParseError if the
        payload cannot be parsed at all."""
        raise NotImplementedError
