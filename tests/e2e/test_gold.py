"""End-to-end — full pipeline output vs the gold profile (doc 07).

THE most important test. Default config output must equal gold-profile.json for
every field EXCEPT the two explicitly-named documented gaps:
  GAP 1 — overall_confidence: 0.74 (consistent) vs gold 0.79
  GAP 2 — skills.PostgreSQL provenance: missing ';notes_dispute'
"""
import contextlib
import copy
import io
import json
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "src"))

from transformer.models import Config  # noqa: E402
from transformer.pipeline import transform  # noqa: E402


class TestGoldProfile(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cfg = Config.from_dict(json.loads((ROOT / "configs" / "default-config.json").read_text()))
        sources = [
            ("ats", (ROOT / "fixtures" / "ats.json").read_text()),
            ("notes", (ROOT / "fixtures" / "recruiter-notes.txt").read_text()),
        ]
        with contextlib.redirect_stderr(io.StringIO()):
            outputs, cls.failures = transform(sources, cfg)
        # single candidate -> exactly one profile in the list
        assert len(outputs) == 1, f"expected 1 profile, got {len(outputs)}"
        cls.output = outputs[0]
        cls.gold = json.loads((ROOT / "fixtures" / "gold-profile.json").read_text())

    def test_no_failures(self):
        self.assertEqual(self.failures, [])

    def test_output_equals_gold_with_two_documented_gaps(self):
        expected = copy.deepcopy(self.gold)

        # GAP 1 (documented): overall_confidence 0.74 vs gold 0.79
        self.assertEqual(self.gold["overall_confidence"], 0.79)
        self.assertEqual(self.output["overall_confidence"], 0.74)
        expected["overall_confidence"] = 0.74

        # GAP 2 (documented): skills.PostgreSQL provenance lacks ';notes_dispute'
        for entry in expected["provenance"]:
            if entry["field"] == "skills.PostgreSQL":
                self.assertEqual(entry["method"], "union;single_source;notes_dispute")
                entry["method"] = "union;single_source"

        # Everything else must match the gold EXACTLY (including provenance order)
        self.assertEqual(self.output, expected)


if __name__ == "__main__":
    unittest.main()
