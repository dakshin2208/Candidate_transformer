"""Unit tests — Conflict Resolution Engine (doc 04, doc 07)."""
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "src"))

from transformer.parsers import ATSParser, NotesParser  # noqa: E402
from transformer.matcher import match  # noqa: E402
from transformer.merge import merge  # noqa: E402
from transformer import conflict, confidence  # noqa: E402


class TestConflict(unittest.TestCase):
    def setUp(self):
        ats = ATSParser().parse((ROOT / "fixtures" / "ats.json").read_text())
        notes = NotesParser().parse((ROOT / "fixtures" / "recruiter-notes.txt").read_text())
        self.merged = merge(match([ats, notes]))[0]
        self.resolved = conflict.resolve(self.merged)

    def test_experience_company_ats_wins_databricks_loses(self):
        self.assertEqual(self.resolved.experience[0].company, "Stripe")
        ev = next(e for e in self.resolved.evidence if e.path == "experience[0].company")
        self.assertEqual(ev.winner, "ats")
        self.assertEqual(ev.losing, (("notes", "Databricks"),))

    def test_skills_union_sources(self):
        sources = {s.name: tuple(s.sources) for s in self.resolved.skills}
        self.assertEqual(sources["Python"], ("ats", "notes"))
        self.assertEqual(sources["Kubernetes"], ("ats", "notes"))
        self.assertEqual(sources["Go"], ("notes",))
        self.assertEqual(sources["Rust"], ("notes",))

    def test_postgresql_ats_only_confidence_040(self):
        sources = {s.name: tuple(s.sources) for s in self.resolved.skills}
        self.assertEqual(sources["PostgreSQL"], ("ats",))
        conf = confidence.score(self.resolved).per_field
        self.assertEqual(conf["skills.PostgreSQL"], 0.40)  # not 0.70

    def test_determinism(self):
        again = conflict.resolve(self.merged)
        self.assertEqual(again, self.resolved)


if __name__ == "__main__":
    unittest.main()
