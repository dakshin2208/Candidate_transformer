"""Unit tests — Candidate Matching Engine (doc 04, doc 07)."""
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "src"))

from transformer.matcher import match  # noqa: E402
from transformer.models import SourceRecord  # noqa: E402


class TestMatcher(unittest.TestCase):
    def test_email_match_priority_1(self):
        a = SourceRecord(source="ats", full_name="A", emails=["x@y.com"])
        b = SourceRecord(source="notes", full_name="B", emails=["x@y.com"])
        clusters = match([a, b])
        self.assertEqual(len(clusters), 1)
        m = clusters[0].match
        self.assertEqual((m.key, m.priority, m.strength, m.weak), ("email", 1, "very_high", False))

    def test_name_employer_match_priority_5_weak(self):
        a = SourceRecord(source="ats", full_name="Jane Doe", current_employer="Acme")
        b = SourceRecord(source="notes", full_name="Jane Doe", current_employer="Acme")
        clusters = match([a, b])
        self.assertEqual(len(clusters), 1)
        m = clusters[0].match
        self.assertEqual((m.key, m.priority, m.strength, m.weak), ("name+employer", 5, "medium", True))

    def test_phone_safeguard_names_disagree(self):
        a = SourceRecord(source="ats", full_name="Priya Sharma", phones=["(415) 555-0142"])
        b = SourceRecord(source="notes", full_name="John Doe", phones=["+1 415-555-0142"])
        self.assertEqual(len(match([a, b])), 2)  # suppressed -> two singletons

    def test_phone_match_names_agree(self):
        a = SourceRecord(source="ats", full_name="Priya Sharma", phones=["(415) 555-0142"])
        b = SourceRecord(source="notes", full_name="Priya Sharma", phones=["+1 415-555-0142"])
        clusters = match([a, b])
        self.assertEqual(len(clusters), 1)
        self.assertEqual(clusters[0].match.priority, 4)

    def test_source_order_independence(self):
        a = SourceRecord(source="ats", full_name="A", emails=["x@y.com"])
        b = SourceRecord(source="notes", full_name="B", emails=["x@y.com"])
        self.assertEqual(match([a, b]), match([b, a]))


if __name__ == "__main__":
    unittest.main()
