"""Unit tests — Provenance Tracker (doc 04, doc 07): method strings vs gold."""
import json
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "src"))

from transformer.parsers import ATSParser, NotesParser  # noqa: E402
from transformer.matcher import match  # noqa: E402
from transformer.merge import merge  # noqa: E402
from transformer import conflict, provenance  # noqa: E402


class TestProvenance(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        ats = ATSParser().parse((ROOT / "fixtures" / "ats.json").read_text())
        notes = NotesParser().parse((ROOT / "fixtures" / "recruiter-notes.txt").read_text())
        resolved = conflict.resolve(merge(match([ats, notes]))[0])
        cls.prov = {p.field: (p.source, p.method) for p in provenance.build(resolved)}

    def test_emails_agreement(self):
        self.assertEqual(self.prov["emails[0]"], ("ats", "agreement:ats+notes"))

    def test_phones_agreement_with_transform(self):
        self.assertEqual(self.prov["phones[0]"], ("ats", "agreement:ats+notes;normalized:E164"))

    def test_experience_conflict(self):
        self.assertEqual(
            self.prov["experience[0].company"],
            ("ats", "precedence:ats>notes;CONFLICT:notes_asserts_Databricks;flagged"),
        )

    def test_matches_gold_bar_notes_dispute(self):
        """Every gold provenance entry matches, except the documented
        skills.PostgreSQL ';notes_dispute' annotation (M5 gap)."""
        gold = json.loads((ROOT / "fixtures" / "gold-profile.json").read_text())
        for p in gold["provenance"]:
            field, gsrc, gmethod = p["field"], p["source"], p["method"]
            if field == "skills.PostgreSQL":  # DOCUMENTED GAP
                self.assertEqual(self.prov[field], ("ats", "union;single_source"))
                self.assertEqual(gmethod, "union;single_source;notes_dispute")
                continue
            self.assertEqual(self.prov[field], (gsrc, gmethod))


if __name__ == "__main__":
    unittest.main()
