"""Unit tests — Merge Engine (doc 04, doc 07): preserve all evidence, no winners."""
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "src"))

from transformer.parsers import ATSParser, NotesParser  # noqa: E402
from transformer.matcher import match  # noqa: E402
from transformer.merge import merge  # noqa: E402


class TestMerge(unittest.TestCase):
    def setUp(self):
        ats = ATSParser().parse((ROOT / "fixtures" / "ats.json").read_text())
        notes = NotesParser().parse((ROOT / "fixtures" / "recruiter-notes.txt").read_text())
        self.merged = merge(match([ats, notes]))[0]

    def _vals(self, field):
        return [(c.source, c.value) for c in self.merged.fields.get(field, [])]

    def test_employer_conflict_preserved(self):
        self.assertEqual(self._vals("current_employer"),
                         [("ats", "Stripe"), ("notes", "Databricks")])

    def test_all_skill_contributions_preserved(self):
        self.assertEqual(self._vals("skills"), [
            ("ats", "Python"), ("ats", "PostgreSQL"), ("ats", "Kubernetes"),
            ("notes", "Python"), ("notes", "Go"), ("notes", "Kubernetes"), ("notes", "Rust"),
        ])

    def test_raw_values_not_normalized(self):
        self.assertEqual(self._vals("emails"),
                         [("ats", "Priya.Sharma@Gmail.com"), ("notes", "priya.sharma@gmail.com")])


if __name__ == "__main__":
    unittest.main()
