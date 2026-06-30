"""Unit tests — Confidence Engine (doc 04, doc 07)."""
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "src"))

from transformer.parsers import ATSParser, NotesParser  # noqa: E402
from transformer.matcher import match  # noqa: E402
from transformer.merge import merge  # noqa: E402
from transformer.models import SourceRecord  # noqa: E402
from transformer import conflict, confidence  # noqa: E402


class TestConfidence(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        ats = ATSParser().parse((ROOT / "fixtures" / "ats.json").read_text())
        notes = NotesParser().parse((ROOT / "fixtures" / "recruiter-notes.txt").read_text())
        resolved = conflict.resolve(merge(match([ats, notes]))[0])
        cls.conf = confidence.score(resolved).per_field

    def test_two_sources_098(self):
        self.assertEqual(self.conf["skills.Python"], 0.98)
        self.assertEqual(self.conf["skills.Kubernetes"], 0.98)

    def test_single_reliable_source_070(self):
        self.assertEqual(self.conf["skills.Go"], 0.70)
        self.assertEqual(self.conf["skills.Rust"], 0.70)

    def test_single_low_reliability_source_040(self):
        self.assertEqual(self.conf["skills.PostgreSQL"], 0.40)  # ATS low-reliability for skills

    def test_weak_match_minus_015(self):
        # name+employer (priority 5) -> weak; a single-source field under it gets
        # base 0.70 - 0.15 = 0.55.
        a = SourceRecord(source="ats", full_name="Jane Doe", current_employer="Acme", headline="Engineer")
        b = SourceRecord(source="notes", full_name="Jane Doe", current_employer="Acme")
        resolved = conflict.resolve(merge(match([a, b]))[0])
        self.assertTrue(resolved.match.weak)
        conf = confidence.score(resolved).per_field
        self.assertEqual(conf["headline"], 0.55)   # 0.70 base - 0.15 weak penalty


if __name__ == "__main__":
    unittest.main()
