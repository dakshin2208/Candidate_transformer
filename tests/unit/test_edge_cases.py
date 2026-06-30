"""Edge-case hardening — unicode names + unparseable phones (tests only).

Documents actual behavior. Both areas were already correct; the only noted
limitation is that candidate_id's slug is ASCII-only (full_name is preserved
verbatim, deterministic, no crash) — reported, not "fixed", since it is not a bug.
"""
import contextlib
import io
import json
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "src"))

from transformer.models import Config, SourceRecord  # noqa: E402
from transformer.matcher import match  # noqa: E402
from transformer.normalize import normalize_name, normalize_phone  # noqa: E402
from transformer.pipeline import transform  # noqa: E402

DEFAULT = Config.from_dict(json.loads((ROOT / "configs" / "default-config.json").read_text()))
CUSTOM = Config.from_dict(json.loads((ROOT / "configs" / "custom-config.json").read_text()))


def _transform(sources, cfg=DEFAULT):
    with contextlib.redirect_stderr(io.StringIO()):
        return transform(sources, cfg)


class TestUnicodeNames(unittest.TestCase):
    def test_normalize_preserves_unicode(self):
        self.assertEqual(normalize_name("José García"), "José García")
        self.assertEqual(normalize_name("François   Müller"), "François Müller")

    def test_matcher_email_match_with_unicode_names(self):
        a = SourceRecord(source="ats", full_name="José García", emails=["jose@x.com"])
        b = SourceRecord(source="notes", full_name="José García", emails=["jose@x.com"])
        clusters = match([a, b])
        self.assertEqual(len(clusters), 1)
        self.assertEqual(clusters[0].match.key, "email")

    def test_pipeline_unicode_no_crash_fullname_preserved(self):
        ats = json.dumps({"applicant": {
            "fullName": "José García", "contactEmail": "jose@x.com", "mobile": "(212) 555-1212"}})
        outs, _ = _transform([("ats", ats)])
        self.assertEqual(len(outs), 1)
        self.assertEqual(outs[0]["full_name"], "José García")        # preserved verbatim
        # DOCUMENTED limitation: id slug is ASCII-only (non-ASCII -> '-').
        self.assertEqual(outs[0]["candidate_id"], "jos-garc-a-001")


class TestUnparseablePhone(unittest.TestCase):
    def test_normalize_returns_none_cleanly(self):
        for raw in ["ext. 1234", "call my desk", "n/a", "phone: see email"]:
            self.assertIsNone(normalize_phone(raw))

    def test_pipeline_unparseable_phone_empty_then_omitted(self):
        ats = json.dumps({"applicant": {
            "fullName": "Deskbound Dan", "contactEmail": "dan@x.com", "mobile": "ext. 1234"}})
        # default (on_missing=null): phones resolves to an empty list (null-skipped)
        outs_default, _ = _transform([("ats", ats)], DEFAULT)
        self.assertEqual(outs_default[0]["phones"], [])
        # custom (on_missing=omit): primary_phone <- phones[0] is unresolvable -> omitted
        outs_custom, _ = _transform([("ats", ats)], CUSTOM)
        self.assertNotIn("primary_phone", outs_custom[0])


if __name__ == "__main__":
    unittest.main()
