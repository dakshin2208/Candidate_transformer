"""Source parsers (doc 05 Source Parsers, doc 06 M2)."""
from .ats import ATSParser
from .base import SourceParseError, SourceParser
from .notes import NotesParser

__all__ = [
    "SourceParser",
    "SourceParseError",
    "ATSParser",
    "NotesParser",
    "default_parsers",
]


def default_parsers() -> dict:
    """The two built-in core parsers, keyed by source id (doc 06 scope).

    This registry is the extension point: a new source (GitHub, CSV, Resume)
    registers one entry here and needs no engine change (doc 05 Extensibility).
    """
    return {
        ATSParser.source_name: ATSParser(),
        NotesParser.source_name: NotesParser(),
    }
