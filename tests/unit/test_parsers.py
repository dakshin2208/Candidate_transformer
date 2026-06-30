"""Unit tests — Source Parsers (doc 06 M2, doc 07)."""
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "src"))

from transformer.parsers import ATSParser, NotesParser  # noqa: E402
from transformer.parsers.base import SourceParseError  # noqa: E402

ATS_TEXT = (ROOT / "fixtures" / "ats.json").read_text()
NOTES_TEXT = (ROOT / "fixtures" / "recruiter-notes.txt").read_text()


class TestATSParser(unittest.TestCase):
    def setUp(self):
        self.rec = ATSParser().parse(ATS_TEXT)

    def test_field_remapping(self):
        self.assertEqual(self.rec.full_name, "Priya Sharma")          # fullName
        self.assertEqual(self.rec.headline, "Senior Backend Engineer")  # jobTitle
        self.assertEqual(self.rec.current_employer, "Stripe")          # currentEmployer
        self.assertEqual(self.rec.location.region, "CA")              # state -> region
        self.assertEqual(self.rec.experience[0].company, "Stripe")    # employer -> company

    def test_raw_values_preserved(self):
        self.assertEqual(self.rec.emails, ["Priya.Sharma@Gmail.com"])  # NOT lowercased
        self.assertEqual(self.rec.phones, ["(415) 555-0142"])          # NOT E.164'd
        self.assertEqual(self.rec.location.country, "United States")   # NOT 'US'

    def test_malformed_json_raises(self):
        with self.assertRaises(SourceParseError):
            ATSParser().parse("{ broken json :::")

    def test_missing_applicant_raises(self):
        with self.assertRaises(SourceParseError):
            ATSParser().parse('{"not_applicant": 1}')


class TestNotesParser(unittest.TestCase):
    def setUp(self):
        self.rec = NotesParser().parse(NOTES_TEXT)

    def test_email_and_phone(self):
        self.assertEqual(self.rec.emails, ["priya.sharma@gmail.com"])
        self.assertEqual(self.rec.phones, ["+1 415-555-0142"])  # raw

    def test_employer_is_databricks_not_stripe(self):
        self.assertEqual(self.rec.current_employer, "Databricks")

    def test_skills_extracted_postgres_excluded(self):
        self.assertEqual(self.rec.skills, ["Python", "Go", "Kubernetes", "Rust"])
        self.assertNotIn("PostgreSQL", self.rec.skills)  # negated: "Did NOT claim PostgreSQL"

    def test_single_source_fields_not_extracted(self):
        self.assertIsNone(self.rec.full_name)        # header is documentary
        self.assertIsNone(self.rec.location.city)    # "Based in SF" not asserted
        self.assertEqual(self.rec.education, [])      # "Berkeley grad" not fabricated


if __name__ == "__main__":
    unittest.main()
