"""Integration — multi-candidate + duplicate-source + zero-skills (hardening pass).

test_two_distinct_candidates_both_returned is the regression test that would have
caught the original `merged[0]` silent-drop bug.
"""
import contextlib
import io
import json
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "src"))

from transformer.models import Config  # noqa: E402
from transformer.pipeline import transform  # noqa: E402
from transformer.parsers import default_parsers  # noqa: E402
from transformer.validate import parse_sources  # noqa: E402

DEFAULT = Config.from_dict(json.loads((ROOT / "configs" / "default-config.json").read_text()))
PRIYA_ATS = (ROOT / "fixtures" / "ats.json").read_text()
PRIYA_NOTES = (ROOT / "fixtures" / "recruiter-notes.txt").read_text()
# A second person sharing NO match key with Priya (different email/name/phone/employer).
MARCUS_ATS = json.dumps({"applicant": {
    "fullName": "Marcus Lee", "contactEmail": "marcus.lee@corp.io",
    "mobile": "(212) 555-9999", "currentEmployer": "Acme",
    "jobTitle": "Data Engineer", "skillsList": ["Java", "Scala"]}})


def _transform(sources, cfg=DEFAULT):
    with contextlib.redirect_stderr(io.StringIO()):
        return transform(sources, cfg)


class TestMultiCandidate(unittest.TestCase):
    def test_two_distinct_candidates_both_returned(self):
        """Two people, no shared match key -> TWO profiles (regression test)."""
        outs, failures = _transform([("ats", PRIYA_ATS), ("notes", PRIYA_NOTES), ("ats", MARCUS_ATS)])
        self.assertEqual(failures, [])
        self.assertEqual(len(outs), 2)
        self.assertEqual({o["candidate_id"] for o in outs}, {"priya-sharma-001", "marcus-lee-001"})

    def test_duplicate_same_type_sources_both_parsed(self):
        """Two ('ats', ...) entries in one call -> BOTH parsed, none dropped."""
        result = parse_sources([("ats", PRIYA_ATS), ("ats", MARCUS_ATS)], default_parsers())
        self.assertEqual([r.source for r in result.records], ["ats", "ats"])
        self.assertEqual(result.failures, [])

    def test_zero_skills_source_clean_profile(self):
        """A source with no skills -> a clean profile with skills == []."""
        no_skills = json.dumps({"applicant": {
            "fullName": "No Skills", "contactEmail": "ns@x.com", "mobile": "(212) 555-0000"}})
        outs, _ = _transform([("ats", no_skills)])
        self.assertEqual(len(outs), 1)
        self.assertEqual(outs[0]["skills"], [])


if __name__ == "__main__":
    unittest.main()
