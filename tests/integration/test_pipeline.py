"""Integration tests — pipeline.transform over multiple sources (doc 07)."""
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

ATS = (ROOT / "fixtures" / "ats.json").read_text()
NOTES = (ROOT / "fixtures" / "recruiter-notes.txt").read_text()
CONFIG = Config.from_dict(json.loads((ROOT / "configs" / "default-config.json").read_text()))


def _transform(sources):
    """Run transform with the [STAGE] logs muted."""
    with contextlib.redirect_stderr(io.StringIO()):
        return transform(sources, CONFIG)


class TestPipeline(unittest.TestCase):
    def test_ats_and_notes_one_candidate(self):
        outs, failures = _transform([("ats", ATS), ("notes", NOTES)])
        self.assertEqual(failures, [])
        self.assertEqual(len(outs), 1)
        self.assertEqual(outs[0]["candidate_id"], "priya-sharma-001")

    def test_malformed_ats_with_valid_notes_continues(self):
        outs, failures = _transform([("ats", "{ broken json"), ("notes", NOTES)])
        self.assertEqual(len(failures), 1)
        self.assertEqual(failures[0].source, "ats")
        self.assertEqual(len(outs), 1)  # notes alone still produced a profile

    def test_empty_notes_with_valid_ats(self):
        outs, failures = _transform([("notes", "   \n  "), ("ats", ATS)])
        self.assertEqual(len(failures), 1)
        self.assertEqual(failures[0].reason, "empty source")
        self.assertEqual(outs[0]["candidate_id"], "priya-sharma-001")  # ATS still produces output

    def test_unknown_source_reported_and_skipped(self):
        outs, failures = _transform([("linkedin", "whatever"), ("ats", ATS), ("notes", NOTES)])
        self.assertIn("linkedin", [f.source for f in failures])
        self.assertEqual(len(outs), 1)

    def test_all_sources_fail_returns_empty(self):
        outs, failures = _transform([("ats", "{bad"), ("notes", "   ")])
        self.assertEqual(outs, [])
        self.assertEqual(len(failures), 2)


if __name__ == "__main__":
    unittest.main()
